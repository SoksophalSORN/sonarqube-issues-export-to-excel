
# SonarQube Issues Export

This is a fork from talha2k/sonarqube-issues-export-to-excel. I forked it to customize the code for my own use.

This Python script fetches issues from a SonarQube project and exports them to CSV or Excel format. It uses the SonarQube REST API and handles pagination, date ranges, and chunked writing to efficiently retrieve and export large numbers of issues.

**Compatible with both local SonarQube instances (localhost:9000) and SonarCloud.**

For SonarQube Community Edition, branch-aware export requires the `mc1arke/sonarqube-community-branch-plugin` plugin to be installed and working. Without that plugin, the script falls back to a normal project issue export and removes the `branch`, `commit_sha`, and `line_commit_sha` columns.

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

### Basic Usage (CSV format)

```bash
python sonar-export.py
```

This will export issues to `sonarqube_issues.csv` by default.

If no branch is specified, the script lists all project branches and exports issues from each branch.

To choose the report filename:

```bash
python sonar-export.py --output reports/sonarqube-ai.csv
```

If the output filename has no extension, the selected format is appended. For example, `--output reports/sonarqube-ai` writes `reports/sonarqube-ai.csv` by default.

### Export to Excel

You can export to Excel format:

```bash
python sonar-export.py --format xlsx
```

This will export issues to `sonarqube_issues.xlsx`.

You can also infer the format from the output filename:

```bash
python sonar-export.py --output reports/sonarqube-ai.xlsx
```

If the target export file already exists, the script preserves it and writes to the next available numbered filename instead, such as `sonarqube_issues-1.csv`, `sonarqube_issues-2.csv`, or `sonarqube_issues-3.xlsx`.

### Export Options

```bash
python sonar-export.py --format [csv|xlsx] --output <filename>
```

- `-f`, `--format csv|xlsx`: Export to CSV format or Excel format. CSV is the default
- `-o`, `--output <filename>`: Choose the output filename. If no extension is provided, the selected format is appended
- `-b`, `--branch <name>`: Export only this SonarQube branch. On SonarQube CE, this requires the community branch plugin
- `-is`, `--issue-status open|fixed`: Export only rows where `issue_status` is `OPEN` or `FIXED`
- `-s`, `--status open|close`: Export only rows where `status` is `OPEN` or `CLOSED`
- `-m`, `--minimal`: Export only rows where `issue_status` is `OPEN` and `status` is `OPEN`
- `-q`, `--quiet`: Suppress progress messages and print only the final export summary

`--issue-status` and `--status` can be used together in any order. If neither is specified, the script exports every issue returned by SonarQube. `--minimal` must be used by itself and cannot be combined with `--issue-status` or `--status`.

For CI jobs, the script exits with code `0` when the export completes successfully, including when no issues match the selected filters. It exits with code `1` for configuration, dependency, fetch, or file-write failures.

Examples:

```bash
# Export only currently open actionable issues
python sonar-export.py -f csv -m

# Export only the main branch
python sonar-export.py -f csv --branch main

# Export fixed issues regardless of the status column
python sonar-export.py -f csv -is fixed

# Export only rows where both filters match
python sonar-export.py -f csv -is open -s open

# Generate a quiet AI-agent report with a custom filename
python sonar-export.py -q -m -o reports/sonarqube-ai.csv
```

In quiet mode, successful exports print only the final summary:

```text
✅ Export completed: 2149 issues exported to sonarqube_issues.csv
📥 Total issues fetched before filters: 2149
📊 Date range: 2000-01-01 to 2026-07-02
```

## Features

- **Multiple Export Formats**: Export to CSV or Excel (XLSX) format
- **Custom Output Filename**: Choose the report filename with `--output`
- **Safe Export Filenames**: Avoids overwriting existing exports by adding a numbered suffix when needed
- **AI-Friendly Columns**: Exports a stable set of issue columns for AI-agent triage and fixing
- **Branch-Aware Export**: Exports all SonarQube branches by default, or one branch when `--branch` is provided. On SonarQube CE, this requires the community branch plugin
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
- **Quiet Mode**: Use `--quiet` or `-q` to print only the final export summary

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

On SonarQube CE, these branch and revision metadata columns depend on the community branch plugin. If the plugin is not installed or the branch endpoints are unavailable, the script still exports issues but removes `branch`, `commit_sha`, and `line_commit_sha` from the report.

Nested SonarQube fields such as `textRange`, `flows`, and `impacts` are stored as JSON strings so AI agents can preserve secondary locations and issue-flow context.

## Example

Complete workflow example:

### Using Local SonarQube Instance

```bash
# Set up environment variables for local instance
export SONAR_URL='http://localhost:9000/api/issues/search'
export SONAR_PROJECT_KEY='my-project'
export SONAR_TOKEN='your-token-here'

# Export to CSV (default)
python sonar-export.py

# Export to Excel
python sonar-export.py --format xlsx
```

### Using SonarCloud

```bash
# Set up environment variables for SonarCloud
export SONAR_URL='https://sonarcloud.io/api/issues/search'
export SONAR_PROJECT_KEY='my-project'
export SONAR_TOKEN='your-token-here'

# Export to CSV (default)
python sonar-export.py

# Export to Excel
python sonar-export.py --format xlsx
```

Example output:
```text
Fetching issues for branch 'main' from 2000-01-01 to 2000-01-31...
Fetched 1234 issues so far; 1200 matched export filters...
...
✅ Export completed: 7891 issues exported to sonarqube_issues.csv
📥 Total issues fetched before filters: 8000
📊 Date range: 2000-01-01 to 2026-07-02
```

## Customization

You can customize the date range and other parameters by editing the script:

- `start_date`: Change the start date for issue retrieval (default: 2025-01-01)
- `end_date`: Change the end date (default: current date)
- `delta`: Adjust the date range chunk size (default: 30 days)
- `chunk_size`: Change how often data is written to disk (default: 5000 issues)

## License

This project is licensed under the MIT License.
