# Repository Synchronization Solution

## Problem Statement
When repositories are added to or removed from the Overview page (`services_links.yml`), the data files need to be updated accordingly:
- **New repositories**: Download their full history
- **Removed repositories**: Clean up their data from the JSON files
- **Existing repositories**: Continue with incremental updates

## Solution Overview
The solution implements **smart repository synchronization** that automatically detects changes and handles them appropriately during incremental data updates.

---

## Implementation Details

### GitHub Service (`services/github_service.py`)

#### Modified Methods:

**1. `get_missing_merged_pull_requests()`**
- Detects new and removed repositories by comparing current `services_links.yml` with existing data
- **Removed repos**: Deletes their data from the JSON file
- **New repos**: Downloads their full PR history using `_download_merged_prs_for_repos()`
- **Existing repos**: Continues with incremental update (since last timestamp)

**2. `get_missing_closed_pull_requests()`**
- Same logic as merged PRs, but for closed (not merged) PRs

#### New Helper Methods:

**3. `_download_merged_prs_for_repos(repos_list, full_history=True)`**
- Downloads all merged PRs for specific repositories
- Uses GraphQL queries with pagination
- Handles errors gracefully per repository

**4. `_download_closed_prs_for_repos(repos_list, full_history=True)`**
- Downloads all closed PRs for specific repositories
- Uses GraphQL queries with pagination
- Handles errors gracefully per repository

### GitLab Service (`services/gitlab_service.py`)

#### Modified Methods:

**1. `add_missing_merge_requests(new_mrs)`**
- Detects new and removed repositories
- **Removed repos**: Deletes their data from the JSON file
- **New repos**: Downloads their full MR history using `_download_mrs_for_specific_repos()`
- **Existing repos**: Adds incremental updates from `new_mrs` parameter

**2. `add_missing_closed_merge_requests(new_mrs)`**
- Same logic as merged MRs, but for closed (not merged) MRs

#### New Helper Method:

**3. `_download_mrs_for_specific_repos(repos_list, **kvargs)`**
- Downloads MRs for specific repositories
- Supports all merge request states (merged, closed, open)
- Handles errors gracefully per repository

---

## Workflow Example

### Scenario: Adding a New Repository

1. User adds `https://github.com/myorg/new-repo` to `services_links.yml`
2. User clicks "Update Data" button (incremental update)
3. System detects:
   - `new-repo` is in `services_links.yml`
   - `new-repo` is NOT in existing `github_merged_pr_list.json`
4. Logs: `🆕 Detected 1 new repositories: ['new-repo']`
5. System downloads **full history** for `new-repo`:
   - `📥 Downloading full history for 1 new repositories...`
   - `✅ Downloaded 150 merged PRs for new repository: new-repo`
6. For all existing repos, system performs incremental update (since last timestamp)
7. Final log: `📊 Summary: 25 repositories tracked, 5000 total merged PRs`

### Scenario: Removing a Repository

1. User removes `https://github.com/myorg/old-repo` from `services_links.yml`
2. User clicks "Update Data" button (incremental update)
3. System detects:
   - `old-repo` is in existing `github_merged_pr_list.json`
   - `old-repo` is NOT in `services_links.yml`
4. Logs: `🗑️  Detected 1 removed repositories: ['old-repo']`
5. System removes data: `✅ Removed data for repository: old-repo`
6. Data is cleaned from the JSON file

### Scenario: No Changes (Normal Incremental Update)

1. User clicks "Update Data" button
2. System detects no new or removed repositories
3. System performs incremental update for all existing repositories
4. Logs: `🔄 Performing incremental update for 24 existing repositories...`
5. System fetches only PRs updated since last timestamp

---

## Benefits

✅ **Automatic Detection**: No manual intervention needed
✅ **Efficient**: Only downloads full history for new repos
✅ **Clean**: Automatically removes stale data
✅ **Safe**: Handles errors gracefully per repository
✅ **Informative**: Detailed logging of all operations
✅ **Consistent**: Same approach for GitHub and GitLab

---

## Affected Data Files

### GitHub:
- `data/github_merged_pr_list.json`
- `data/github_closed_pr_list.json`

### GitLab:
- `data/gitlab_merged_pr_list.json`
- `data/gitlab_closed_pr_list.json`

### Note on Open PRs:
Open PRs are always downloaded from scratch (full download), so they automatically sync with `services_links.yml` without special handling.

---

## Logging Output

The solution provides clear, emoji-enhanced logging:

- 🆕 New repositories detected
- 🗑️ Removed repositories detected
- 📥 Downloading full history
- ✅ Success messages
- ❌ Error messages
- 🔄 Incremental update in progress
- 📊 Summary statistics

---

## Testing Recommendations

1. **Add a new repository**:
   - Add new repo to `services_links.yml`
   - Click "Update Data"
   - Verify full history is downloaded
   - Check logs for detection message

2. **Remove a repository**:
   - Remove repo from `services_links.yml`
   - Click "Update Data"
   - Verify data is removed from JSON
   - Check logs for removal message

3. **Normal update (no changes)**:
   - Keep `services_links.yml` unchanged
   - Click "Update Data"
   - Verify only incremental updates occur
   - Verify no new/removed repo messages

4. **Multiple changes**:
   - Add 2 new repos and remove 1 old repo
   - Click "Update Data"
   - Verify all changes are handled correctly

---

## Future Enhancements (Optional)

- Add UI notification when new repos are detected
- Create a "Sync Status" panel showing last sync details
- Add ability to force full re-download for specific repos
- Track sync history in a separate log file
