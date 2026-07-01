try:
    import pandas as pd
    import requests
    import os
    import argparse
    import json
    from datetime import datetime, timedelta
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Run: pip install requests pandas openpyxl")
    exit(1)

# SonarQube parameters
load_dotenv()

SONARQUBE_URL = os.getenv('SONAR_URL', 'http://localhost:9000/api/issues/search') #Sonar Instance URL
PROJECT_KEY = os.getenv('SONAR_PROJECT_KEY', '') #Your Project Key
TOKEN = os.getenv('SONAR_TOKEN', '') #Your Project Token

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Export SonarQube issues to CSV or Excel format')
parser.add_argument('--format', type=str, choices=['csv', 'xlsx'], default='xlsx',
                    help='Output format: csv or xlsx (default: xlsx)')
parser.add_argument('--branch', type=str, default=os.getenv('SONAR_BRANCH', ''),
                    help='Export only this SonarQube branch. If omitted, all project branches are exported')
parser.add_argument('--issue-status', type=str, choices=['open', 'fixed'],
                    help='Export only issues with this issue_status value')
parser.add_argument('--status', type=str, choices=['open', 'close', 'closed'],
                    help='Export only issues with this status value')
parser.add_argument('--minimal', action='store_true',
                    help='Export only issues where issue_status is OPEN and status is OPEN')
args = parser.parse_args()

if args.minimal and (args.issue_status or args.status):
    parser.error('--minimal cannot be used with --issue-status or --status')

# Add basic input validation after argument parsing so --help can run without credentials.
if not PROJECT_KEY or not TOKEN:
    parser.error('SONAR_PROJECT_KEY and SONAR_TOKEN must be configured')

ISSUE_STATUS_FILTERS = {
    'open': 'OPEN',
    'fixed': 'FIXED',
}

STATUS_FILTERS = {
    'open': 'OPEN',
    'close': 'CLOSED',
    'closed': 'CLOSED',
}

if args.minimal:
    ISSUE_STATUS_FILTER = 'OPEN'
    STATUS_FILTER = 'OPEN'
else:
    ISSUE_STATUS_FILTER = ISSUE_STATUS_FILTERS.get(args.issue_status)
    STATUS_FILTER = STATUS_FILTERS.get(args.status)

OUTPUT_COLUMNS = [
    'branch',
    'commit_sha',
    'line_commit_sha',
    'analysis_date',
    'issue_key',
    'rule',
    'severity',
    'impact_severity',
    'software_quality',
    'type',
    'status',
    'issue_status',
    'component',
    'file_path',
    'line',
    'message',
    'textRange',
    'flows',
    'creationDate',
    'updateDate',
    'impacts',
]

SEVERITY_ORDER = {
    'BLOCKER': 0,
    'CRITICAL': 1,
    'HIGH': 2,
    'MAJOR': 3,
    'MEDIUM': 4,
    'MINOR': 5,
    'LOW': 6,
    'INFO': 7,
}


def json_cell(value):
    if value in (None, ''):
        return ''
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def join_unique(values):
    clean_values = []
    for value in values:
        if value and value not in clean_values:
            clean_values.append(value)
    return '; '.join(clean_values)


def sort_severities(severities):
    return sorted(severities, key=lambda value: SEVERITY_ORDER.get(value, 99))


def file_path_from_component(component):
    if not component:
        return ''
    if ':' in component:
        return component.split(':', 1)[1]
    return component


def sonar_server_url():
    issues_endpoint = '/api/issues/search'
    url = SONARQUBE_URL.rstrip('/')
    if url.endswith(issues_endpoint):
        return url[:-len(issues_endpoint)]
    return url


SONAR_SERVER_URL = sonar_server_url()


def api_url(path):
    return f"{SONAR_SERVER_URL}{path}"


def request_json(url, params, error_context):
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        if response.status_code != 200:
            print(f"❌ Failed to {error_context}: HTTP {response.status_code}")
            print('Response content:', response.text)
            return None
        return response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON while trying to {error_context}: {e}")
    except requests.exceptions.Timeout:
        print(f"❌ Connection timed out while trying to {error_context}.")
    except requests.exceptions.ConnectionError:
        print(f"❌ Connection error while trying to {error_context}.")
    except Exception as e:
        print(f"❌ Unexpected error while trying to {error_context}: {e}")
    return None


def list_project_branches():
    if args.branch:
        return [{'name': args.branch, 'isMain': False, 'analysisDate': ''}]

    data = request_json(
        api_url('/api/project_branches/list'),
        {'project': PROJECT_KEY},
        'list project branches'
    )
    if not data:
        return []

    branches = data.get('branches', [])
    return [branch for branch in branches if branch.get('name')]


def get_latest_branch_analysis(branch):
    branch_name = branch.get('name', '')
    params = {
        'project': PROJECT_KEY,
        'branch': branch_name,
        'ps': 1,
        'p': 1,
    }
    data = request_json(
        api_url('/api/project_analyses/search'),
        params,
        f"get latest analysis for branch '{branch_name}'"
    )

    analyses = data.get('analyses', []) if data else []
    if analyses:
        latest_analysis = analyses[0]
        return {
            'revision': latest_analysis.get('revision', ''),
            'date': latest_analysis.get('date', branch.get('analysisDate', '')),
        }

    return {
        'revision': '',
        'date': branch.get('analysisDate', ''),
    }


line_commit_cache = {}


def issue_line(issue):
    line = issue.get('line')
    if line:
        return line

    text_range = issue.get('textRange') or {}
    if isinstance(text_range, dict):
        return text_range.get('startLine', '')

    return ''


def get_line_commit_sha(issue, branch_name):
    component = issue.get('component')
    line = issue_line(issue)
    if not component or not line:
        return ''

    cache_key = (branch_name, component, line)
    if cache_key in line_commit_cache:
        return line_commit_cache[cache_key]

    params = {
        'key': component,
        'branch': branch_name,
        'from': line,
        'to': line,
    }
    data = request_json(
        api_url('/api/sources/lines'),
        params,
        f"get SCM revision for {component}:{line} on branch '{branch_name}'"
    )

    sources = data.get('sources', []) if data else []
    line_commit_sha = ''
    if sources:
        line_commit_sha = sources[0].get('scmRevision', '')

    line_commit_cache[cache_key] = line_commit_sha
    return line_commit_sha


def enrich_issue(issue, branch, branch_analysis):
    enriched_issue = dict(issue)
    branch_name = branch.get('name', '')
    enriched_issue['_export_branch'] = branch_name
    enriched_issue['_analysis_commit_sha'] = branch_analysis.get('revision', '')
    enriched_issue['_analysis_date'] = branch_analysis.get('date', '')
    enriched_issue['_line_commit_sha'] = get_line_commit_sha(issue, branch_name)
    return enriched_issue


def should_export_issue(issue):
    if ISSUE_STATUS_FILTER and issue.get('issueStatus') != ISSUE_STATUS_FILTER:
        return False
    if STATUS_FILTER and issue.get('status') != STATUS_FILTER:
        return False
    return True


def normalize_issue(issue):
    impacts = issue.get('impacts') or []
    impact_severities = sort_severities(
        impact.get('severity') for impact in impacts if isinstance(impact, dict)
    )
    software_qualities = [
        impact.get('softwareQuality') for impact in impacts if isinstance(impact, dict)
    ]

    return {
        'branch': issue.get('_export_branch', issue.get('branch', '')),
        'commit_sha': issue.get('_analysis_commit_sha', ''),
        'line_commit_sha': issue.get('_line_commit_sha', ''),
        'analysis_date': issue.get('_analysis_date', ''),
        'issue_key': issue.get('key', ''),
        'rule': issue.get('rule', ''),
        'severity': issue.get('severity', ''),
        'impact_severity': join_unique(impact_severities),
        'software_quality': join_unique(software_qualities),
        'type': issue.get('type', ''),
        'status': issue.get('status', ''),
        'issue_status': issue.get('issueStatus', ''),
        'component': issue.get('component', ''),
        'file_path': file_path_from_component(issue.get('component', '')),
        'line': issue.get('line', ''),
        'message': issue.get('message', ''),
        'textRange': json_cell(issue.get('textRange')),
        'flows': json_cell(issue.get('flows')),
        'creationDate': issue.get('creationDate', ''),
        'updateDate': issue.get('updateDate', ''),
        'impacts': json_cell(impacts),
    }


def normalize_issues(issues):
    return [normalize_issue(issue) for issue in issues]


def get_available_filename(filename):
    if not os.path.exists(filename):
        return filename

    base, ext = os.path.splitext(filename)
    counter = 1

    while os.path.exists(f'{base}-{counter}{ext}'):
        counter += 1

    return f'{base}-{counter}{ext}'


# Function to write data in chunks to CSV
def write_chunk_to_csv(filename, chunk_data, mode='w'):
    """
    Write a chunk of issue data to a CSV file.

    Parameters:
        filename (str): The path to the output CSV file.
        chunk_data (list): List of issue dictionaries to write.
        mode (str): File write mode, 'w' for write (creates new file), 'a' for append.

    Behavior:
        - Converts chunk_data to a pandas DataFrame.
        - Writes the DataFrame to the specified CSV file.
        - If mode is 'w', includes the header; if 'a', omits the header.
    """
    df = pd.DataFrame(normalize_issues(chunk_data), columns=OUTPUT_COLUMNS)
    # For CSV, we can simply append with or without header
    df.to_csv(filename, index=False, mode=mode, header=(mode == 'w'))

# Function to write data in chunks to Excel
def write_chunk_to_excel(filename, chunk_data, mode='w'):
    df = pd.DataFrame(normalize_issues(chunk_data), columns=OUTPUT_COLUMNS)
    if mode == 'w':
        # First chunk: create new file
        df.to_excel(filename, index=False, engine='openpyxl')
    else:
        # Subsequent chunks: append to existing file without headers
        with pd.ExcelWriter(filename, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
            # Get the current number of rows
            book = writer.book
            sheet = book.active
            startrow = sheet.max_row
            # Write the new data
            df.to_excel(writer, index=False, header=False, startrow=startrow)

# Fetch issues from SonarQube
headers = {"Authorization": f'Bearer {TOKEN}'}
page_size = 500  # Page size, maximum allowed by SonarQube

# Adjust date ranges as necessary to ensure each range returns less than 10,000 issues
start_date = datetime(2000, 1, 1)  # Example start date
end_date = datetime.now()  # Current date and time
delta = timedelta(days=30)  # Adjust the range to ensure < 10,000 results

current_start_date = start_date
all_issues = []
requested_output_file = f'sonarqube_issues.{args.format}'
output_file = get_available_filename(requested_output_file)
if output_file != requested_output_file:
    print(f"Output file '{requested_output_file}' already exists. Exporting to '{output_file}' instead.")
chunk_size = 5000  # Write to file every 5000 issues
write_mode = 'w'  # Start with write mode for the first chunk
total_issues_count = 0
total_exported_count = 0

# Select the appropriate write function based on format
write_function = write_chunk_to_csv if args.format == 'csv' else write_chunk_to_excel

branches = list_project_branches()
if not branches:
    print('No branches found to export.')

for branch in branches:
    branch_name = branch.get('name', '')
    branch_analysis = get_latest_branch_analysis(branch)
    current_start_date = start_date

    print(f"Exporting branch '{branch_name}'...")

    while current_start_date < end_date:
        current_end_date = current_start_date + delta
        if current_end_date > end_date:
            current_end_date = end_date

        print(
            f"Fetching issues for branch '{branch_name}' from "
            f"{current_start_date.strftime('%Y-%m-%d')} to {current_end_date.strftime('%Y-%m-%d')}..."
        )

        params = { #Adjust as required
            'componentKeys': PROJECT_KEY,
            'branch': branch_name,
            'createdAfter': current_start_date.strftime('%Y-%m-%d'),
            'createdBefore': current_end_date.strftime('%Y-%m-%d'),
            'ps': page_size,
            'p': 1
        }

        while True:
            data = request_json(
                api_url('/api/issues/search'),
                params,
                f"fetch issues for branch '{branch_name}'"
            )
            if data is None:
                break

            issues = data.get('issues', [])
            filtered_issues = [
                enrich_issue(issue, branch, branch_analysis)
                for issue in issues
                if should_export_issue(issue)
            ]
            all_issues.extend(filtered_issues)
            total_issues_count += len(issues)
            total_exported_count += len(filtered_issues)

            # Write to file in chunks to save memory
            if len(all_issues) >= chunk_size:
                print(f"Writing chunk of {len(all_issues)} issues to {args.format.upper()}...")
                write_function(output_file, all_issues, write_mode)
                all_issues = []  # Clear memory
                write_mode = 'a'  # Switch to append mode after first write

            # Check if there are more pages
            if len(issues) < page_size:
                break  # No more pages
            else:
                params['p'] += 1  # Next page

        current_start_date = current_end_date
        print(f"Fetched {total_issues_count} issues so far; {total_exported_count} matched export filters...")

# Handle any remaining issues
if all_issues:
    print(f"Writing final chunk of {len(all_issues)} issues to {args.format.upper()}...")
    write_function(output_file, all_issues, write_mode)

if total_exported_count > 0:
    print(f'✅ Export completed: {total_exported_count} issues exported to {output_file}')
    print(f'📥 Total issues fetched before filters: {total_issues_count}')
    print(f'📊 Date range: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
else:
    print('No issues matched the selected export filters.')
