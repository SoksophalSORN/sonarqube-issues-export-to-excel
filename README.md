
# SonarQube Issues Export

This is a fork from talha2k/sonarqube-issues-export-to-excel. I forked it to customize the code for my own use.

This Python script fetches issues from a SonarQube project and exports them to CSV or Excel format. It uses the SonarQube REST API and handles pagination, date ranges, and chunked writing to efficiently retrieve and export large numbers of issues.

**Compatible with both local SonarQube instances (localhost:9000) and SonarCloud.**

## Prerequisites

- Python 3.x
- `requests`, `pandas`, `openpyxl`, `python-dotenv` libraries
- Access to a SonarQube instance with an appropriate token

## Installation

1. Clone the repository:

```bash
git clone https://github.com/talha2k/sonarqube-issues-export-to-excel.git
cd sonarqube-issues-export-to-excel
```

2. Set up python venv

```bash
python -m venv .venv # install venv for this project
source .venv/bin/activate 
which pip # make sure that it does not use system's pip (/usr/bin/pip)
```

3. Install the requirements
```bash
pip install -r requirements.txt
```

## Configuration

Configure the script using environment variables. The script works with both local SonarQube instances and SonarCloud.

### For Local SonarQube Instance (default)

```bash
export SONAR_URL='http://localhost:9000/api/issues/search'   # Local SonarQube instance
export SONAR_PROJECT_KEY='your-project-key'                  # Your project key
export SONAR_TOKEN='your-authentication-token'               # Your authentication token
export SONAR_BRANCH='main'                                   # Optional: export only one branch
```

### For SonarCloud

```bash
export SONAR_URL='https://sonarcloud.io/api/issues/search'   # SonarCloud instance
export SONAR_PROJECT_KEY='your-project-key'                  # Your project key
export SONAR_TOKEN='your-authentication-token'               # Your authentication token
export SONAR_BRANCH='main'                                   # Optional: export only one branch
```

Alternatively, you can edit these values directly in the script.

## Usage

### Basic Usage (Excel format)

```bash
python sonar-export.py
```

This will export issues to `sonarqube_issues.xlsx` by default.

If no branch is specified, the script lists all project branches and exports issues from each branch.

### Export to CSV

For better cross-platform compatibility, you can export to CSV format:

```bash
python sonar-export.py --format csv
```

This will export issues to `sonarqube_issues.csv`.

If the target export file already exists, the script preserves it and writes to the next available numbered filename instead, such as `sonarqube_issues-1.csv`, `sonarqube_issues-2.csv`, or `sonarqube_issues-3.xlsx`.

### Export Options

```bash
python sonar-export.py --format [csv|xlsx]
```

- `--format csv`: Export to CSV format (better cross-platform compatibility, smaller file size)
- `--format xlsx`: Export to Excel format (default, better for viewing in spreadsheet applications)
- `--branch <name>`: Export only this SonarQube branch. If omitted, all project branches are exported
- `--issue-status open|fixed`: Export only rows where `issue_status` is `OPEN` or `FIXED`
- `--status open|close`: Export only rows where `status` is `OPEN` or `CLOSED`
- `--minimal`: Export only rows where `issue_status` is `OPEN` and `status` is `OPEN`

`--issue-status` and `--status` can be used together in any order. If neither is specified, the script exports every issue returned by SonarQube. `--minimal` must be used by itself and cannot be combined with `--issue-status` or `--status`.

Examples:

```bash
# Export only currently open actionable issues
python sonar-export.py --format csv --minimal

# Export only the main branch
python sonar-export.py --format csv --branch main

# Export fixed issues regardless of the status column
python sonar-export.py --format csv --issue-status fixed

# Export only rows where both filters match
python sonar-export.py --format csv --issue-status open --status open
```

## Features

- **Multiple Export Formats**: Export to CSV or Excel (XLSX) format
- **Safe Export Filenames**: Avoids overwriting existing exports by adding a numbered suffix when needed
- **AI-Friendly Columns**: Exports a stable set of issue columns for AI-agent triage and fixing
- **Branch-Aware Export**: Exports all SonarQube branches by default, or one branch when `--branch` is provided
- **Revision Metadata**: Adds the analysis commit SHA and line-level SCM revision when SonarQube provides them
- **Chunked Writing**: Writes data in chunks (every 5000 issues) to minimize memory usage for large exports
- **Date Range Handling**: Automatically splits requests into date ranges to handle SonarQube's 10,000 result limit
- **Pagination Support**: Handles pagination to fetch all issues within each date range
- **Comprehensive Error Handling**: Includes specific error messages for common issues:
  - Authentication failures (401)
  - Project not found (404)
  - Access denied (403)
  - Connection timeouts
  - Network errors
- **Environment Variable Support**: Configure via environment variables for better security
- **Progress Reporting**: Shows real-time progress during export

## Exported Columns

The report includes these columns:

```text
branch
commit_sha
line_commit_sha
analysis_date
issue_key
rule
severity
impact_severity
software_quality
type
status
issue_status
component
file_path
line
message
textRange
flows
creationDate
updateDate
impacts
```

`branch` is the SonarQube branch analyzed for the issue. `commit_sha` is the Git revision of the SonarQube analysis for that branch. `line_commit_sha` is the Git revision that last touched the flagged line when SonarQube SCM data is available.

Nested SonarQube fields such as `textRange`, `flows`, and `impacts` are stored as JSON strings so AI agents can preserve secondary locations and issue-flow context.

## Example

Complete workflow example:

### Using Local SonarQube Instance

```bash
# Set up environment variables for local instance
export SONAR_URL='http://localhost:9000/api/issues/search'
export SONAR_PROJECT_KEY='my-project'
export SONAR_TOKEN='your-token-here'

# Export to Excel (default)
python sonar-export.py

# Export to CSV for cross-platform compatibility
python sonar-export.py --format csv
```

### Using SonarCloud

```bash
# Set up environment variables for SonarCloud
export SONAR_URL='https://sonarcloud.io/api/issues/search'
export SONAR_PROJECT_KEY='my-project'
export SONAR_TOKEN='your-token-here'

# Export to Excel (default)
python sonar-export.py

# Export to CSV for cross-platform compatibility
python sonar-export.py --format csv
```

Example output:
```
Fetching issues from 2025-01-01 to 2025-01-31...
Found 1234 issues so far...
Fetching issues from 2025-01-31 to 2025-03-02...
Found 2567 issues so far...
Writing chunk of 5000 issues to CSV...
...
✅ Export completed: 7891 issues exported to sonarqube_issues.csv
📊 Date range: 2025-01-01 to 2025-11-13
```

## Customization

You can customize the date range and other parameters by editing the script:

- `start_date`: Change the start date for issue retrieval (default: 2025-01-01)
- `end_date`: Change the end date (default: current date)
- `delta`: Adjust the date range chunk size (default: 30 days)
- `chunk_size`: Change how often data is written to disk (default: 5000 issues)

## License

This project is licensed under the MIT License.
