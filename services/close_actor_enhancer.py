"""
Service for enhancing existing PR data with close_actor information.
This runs as a separate process to avoid slowing down the main data download.
"""

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse

# Load environment variables from .env file BEFORE importing config
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import config
from utils import load_json_data, save_json_data_and_return

logger = logging.getLogger(__name__)


class CloseActorEnhancer:
    """Service to enhance existing PR data with close_actor information."""

    def __init__(self):
        self.is_running = False
        self.progress = {
            "status": "idle",  # idle, running, completed, error
            "current_file": "",
            "current_repo": "",
            "processed": 0,
            "total": 0,
            "enhanced": 0,
            "failed": 0,
            "start_time": None,
            "end_time": None,
            "error_message": None,
        }
        self.lock = threading.Lock()  # For thread-safe progress updates
        self.session = self._create_optimized_session()
        self.max_workers = 3  # Reduced from 15 to respect GitHub rate limits
        self.rate_limit_delay = 0.2  # Conservative delay between requests (was 0.1)
        self.last_request_time = 0  # Track timing for rate limiting

    def _create_optimized_session(self):
        """Create an optimized requests session with connection pooling and retries."""
        session = requests.Session()

        # Configure retry strategy for resilience
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[429, 500, 502, 503, 504],
        )

        # Configure HTTP adapter with connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy, pool_connections=20, pool_maxsize=50
        )

        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def get_progress(self) -> Dict[str, Any]:
        """Get current enhancement progress."""
        return self.progress.copy()

    def check_existing_data_status(self) -> Dict[str, Any]:
        """Check if existing data already has close_actor information."""
        try:
            # Check if files exist first
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            if not merged_file.exists() or not closed_file.exists():
                missing_files = []
                if not merged_file.exists():
                    missing_files.append("merged PRs")
                if not closed_file.exists():
                    missing_files.append("closed PRs")

                return {
                    "is_enhanced": False,
                    "coverage_percentage": 0,
                    "total_prs": 0,
                    "enhanced_prs": 0,
                    "needs_enhancement": 0,
                    "files_missing": True,
                    "missing_files": missing_files,
                    "reason": f"Missing data files: {' and '.join(missing_files)}",
                }

            # Check both merged and closed PR files
            merged_status = self._check_file_enhancement_status(
                "github_merged_pr_list.json"
            )
            closed_status = self._check_file_enhancement_status(
                "github_closed_pr_list.json"
            )

            # Overall status
            total_prs = merged_status["total_prs"] + closed_status["total_prs"]
            enhanced_prs = merged_status["enhanced_prs"] + closed_status["enhanced_prs"]

            if total_prs == 0:
                return {
                    "is_enhanced": False,
                    "coverage_percentage": 0,
                    "total_prs": 0,
                    "enhanced_prs": 0,
                    "needs_enhancement": 0,
                    "files_missing": False,
                    "reason": "No PR data found in files",
                }

            coverage_percentage = (
                (enhanced_prs / total_prs) * 100 if total_prs > 0 else 0
            )

            # Coverage calculation complete

            # Consider enhanced if coverage is > 90%
            is_enhanced = coverage_percentage > 90

            return {
                "is_enhanced": is_enhanced,
                "coverage_percentage": coverage_percentage,
                "total_prs": total_prs,
                "enhanced_prs": enhanced_prs,
                "needs_enhancement": total_prs - enhanced_prs,
                "files_missing": False,
                "merged_file": merged_status,
                "closed_file": closed_status,
            }

        except Exception as e:
            logger.error(f"Error checking existing data status: {e}")
            return {
                "is_enhanced": False,
                "coverage_percentage": 0,
                "total_prs": 0,
                "enhanced_prs": 0,
                "needs_enhancement": 0,
                "files_missing": False,  # Assume files exist but there's another error
                "reason": f"Error: {str(e)}",
            }

    def _check_file_enhancement_status(self, filename: str) -> Dict[str, Any]:
        """Check enhancement status of a specific file."""
        file_path = Path(f"data/{filename}")

        try:
            data = load_json_data(file_path)
            if not data or "data" not in data:
                return {"total_prs": 0, "enhanced_prs": 0, "coverage_percentage": 0}

            total_prs = 0
            enhanced_prs = 0

            for repo_name, prs in data["data"].items():
                for pr in prs:
                    total_prs += 1
                    if pr.get("close_actor") is not None:
                        enhanced_prs += 1

            coverage_percentage = (
                (enhanced_prs / total_prs) * 100 if total_prs > 0 else 0
            )

            # File status calculated

            return {
                "total_prs": total_prs,
                "enhanced_prs": enhanced_prs,
                "coverage_percentage": coverage_percentage,
                "needs_enhancement": total_prs - enhanced_prs,
            }

        except Exception as e:
            logger.debug(f"Could not check {filename}: {e}")
            return {
                "total_prs": 0,
                "enhanced_prs": 0,
                "coverage_percentage": 0,
                "needs_enhancement": 0,
            }

    def start_enhancement(self) -> Dict[str, Any]:
        """Start the close_actor enhancement process in background."""
        if self.is_running:
            return {"error": "Enhancement already running", "progress": self.progress}

        # Start background thread
        thread = threading.Thread(target=self._run_enhancement)
        thread.daemon = True
        thread.start()

        return {"success": "Enhancement started", "progress": self.progress}

    def stop_enhancement(self) -> Dict[str, Any]:
        """Gracefully stop the enhancement process after current repository completes."""
        if not self.is_running:
            return {"error": "Enhancement not running", "progress": self.progress}

        logger.info(
            "Enhancement stop requested - will stop after current repository completes"
        )
        self.is_running = False
        self.progress["status"] = "stopping"

        return {"success": "Enhancement stopping gracefully", "progress": self.progress}

    def retry_failed_prs(self) -> Dict[str, Any]:
        """Reset failed PRs (close_actor = null) so they can be retried."""
        try:
            retry_count = 0

            # Reset failed merged PRs
            merged_file = Path("data/github_merged_pr_list.json")
            if merged_file.exists():
                data = load_json_data(merged_file)
                if "data" in data:
                    for repo_name, prs in data["data"].items():
                        for pr in prs:
                            if "close_actor" in pr and pr["close_actor"] is None:
                                del pr["close_actor"]  # Remove so it gets retried
                                retry_count += 1
                    save_json_data_and_return(data, merged_file)

            # Reset failed closed PRs
            closed_file = Path("data/github_closed_pr_list.json")
            if closed_file.exists():
                data = load_json_data(closed_file)
                if "data" in data:
                    for repo_name, prs in data["data"].items():
                        for pr in prs:
                            if "close_actor" in pr and pr["close_actor"] is None:
                                del pr["close_actor"]  # Remove so it gets retried
                                retry_count += 1
                    save_json_data_and_return(data, closed_file)

            logger.info(f"Reset {retry_count} failed PRs for retry")
            return {
                "success": f"Reset {retry_count} failed PRs for retry",
                "retry_count": retry_count,
            }

        except Exception as e:
            logger.error(f"Failed to reset failed PRs: {e}")
            return {"error": f"Failed to reset failed PRs: {str(e)}"}

    def _run_enhancement(self):
        """Run the enhancement process."""
        self.is_running = True
        # Calculate total PRs needing enhancement across both files
        total_needing_enhancement = 0
        try:
            merged_status = self._check_file_enhancement_status(
                "github_merged_pr_list.json"
            )
            closed_status = self._check_file_enhancement_status(
                "github_closed_pr_list.json"
            )
            total_needing_enhancement = (
                merged_status["needs_enhancement"] + closed_status["needs_enhancement"]
            )
        except Exception as e:
            logger.warning(f"Could not calculate total enhancement needed: {e}")

        self.progress.update(
            {
                "status": "running",
                "processed": 0,
                "total": total_needing_enhancement,  # Combined total from both files
                "enhanced": 0,
                "failed": 0,
                "start_time": datetime.now().isoformat(),
                "end_time": None,
                "error_message": None,
            }
        )

        try:
            # Enhance merged PRs
            self.progress["current_file"] = "merged PRs"
            merged_enhanced = self._enhance_file("github_merged_pr_list.json")

            # Enhance closed PRs
            self.progress["current_file"] = "closed PRs"
            closed_enhanced = self._enhance_file("github_closed_pr_list.json")

            # Determine final status based on whether process was stopped or completed
            if self.progress["status"] == "stopping":
                final_status = "stopped"
                logger.info(
                    f"Close_actor enhancement stopped: {merged_enhanced + closed_enhanced} PRs enhanced so far"
                )
            else:
                final_status = "completed"
                logger.info(
                    f"Close_actor enhancement completed: {merged_enhanced + closed_enhanced} PRs enhanced"
                )

            self.progress.update(
                {
                    "status": final_status,
                    "end_time": datetime.now().isoformat(),
                    "current_file": "",
                    "current_repo": "",
                }
            )

        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            self.progress.update(
                {
                    "status": "error",
                    "end_time": datetime.now().isoformat(),
                    "error_message": str(e),
                }
            )
        finally:
            self.is_running = False

    def _enhance_file(self, filename: str) -> int:
        """Enhance PRs in a specific file."""
        logger.info(f"Enhancing {filename}")

        # Load existing data
        file_path = Path(f"data/{filename}")
        data = load_json_data(file_path)

        if not data or "data" not in data:
            logger.warning(f"No data found in {filename}")
            return 0

        repos_data = data["data"]
        total_prs_needing_enhancement = 0

        # Count PRs that need enhancement
        for repo_name, prs in repos_data.items():
            for pr in prs:
                if not pr.get("close_actor"):  # Missing or null
                    total_prs_needing_enhancement += 1

        if total_prs_needing_enhancement == 0:
            logger.info(f"No PRs need enhancement in {filename}")
            return 0

        logger.info(
            f"Found {total_prs_needing_enhancement} PRs needing enhancement in {filename}"
        )

        # Enhance each repository
        total_enhanced = 0
        for repo_name, prs in repos_data.items():
            if not self.is_running:  # Allow cancellation
                break

            self.progress["current_repo"] = repo_name
            enhanced_count = self._enhance_repository_prs(repo_name, prs)
            total_enhanced += enhanced_count

            # Save progress periodically (after each repo)
            data["data"][repo_name] = prs
            save_json_data_and_return(data, file_path)

            # Small delay to be respectful to GitHub API
            time.sleep(0.5)

        # Final save
        save_json_data_and_return(data, file_path)
        logger.info(f"Enhanced {total_enhanced} PRs in {filename}")
        return total_enhanced

    def _enhance_repository_prs(self, repo_name: str, prs: List[Dict]) -> int:
        """Enhance PRs for a specific repository using hybrid GraphQL + REST approach."""
        if not prs:
            return 0

        # Get owner/repo from first PR's html_url
        sample_pr = prs[0]
        html_url = sample_pr.get("html_url", "")
        if "github.com/" not in html_url:
            logger.warning(f"Invalid GitHub URL in {repo_name}")
            return 0

        # Parse owner/repo from URL: https://github.com/owner/repo/pull/123
        url_parts = html_url.split("github.com/")[1].split("/")
        if len(url_parts) < 2:
            logger.warning(f"Cannot parse owner/repo from URL: {html_url}")
            return 0

        owner, repo = url_parts[0], url_parts[1]

        # Filter PRs that need enhancement
        prs_to_enhance = [pr for pr in prs if not pr.get("close_actor")]

        if not prs_to_enhance:
            return 0

        # Smart decision: GraphQL for large repos (>10 PRs), REST API for small repos (≤10 PRs)
        GRAPHQL_THRESHOLD = 10
        prs_count = len(prs_to_enhance)
        use_graphql = prs_count > GRAPHQL_THRESHOLD

        logger.info(f"🚀 Smart enhancement for {prs_count} PRs in {owner}/{repo}")
        logger.info(
            f"📊 Strategy: {'GraphQL bulk + REST fallback' if use_graphql else 'REST API only'} (threshold: {GRAPHQL_THRESHOLD} PRs)"
        )

        # Headers for authentication (REST API) - will be created when needed

        # Headers for GraphQL API
        graphql_headers = {
            "Authorization": f"Bearer {config.GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

        enhanced_count = 0

        if use_graphql:
            # STEP 1: Try bulk GraphQL download for large repos
            current_file = self.progress.get("current_file", "").lower()
            pr_type = "merged" if "merged" in current_file else "closed"

            logger.info(
                f"📊 STEP 1: Bulk GraphQL download for {pr_type} PRs in {owner}/{repo}"
            )
            try:
                bulk_close_actors = self._get_bulk_close_actors_graphql(
                    owner, repo, graphql_headers, pr_type
                )
                logger.info(
                    f"✅ GraphQL: Downloaded {len(bulk_close_actors)} close_actor entries"
                )

                # Apply bulk data to our PRs
                bulk_applied = 0
                for pr in prs_to_enhance:
                    pr_number = pr.get("number")
                    if pr_number and pr_number in bulk_close_actors:
                        pr["close_actor"] = bulk_close_actors[pr_number]
                        bulk_applied += 1
                        enhanced_count += 1

                logger.info(
                    f"📈 Applied {bulk_applied} close_actors from GraphQL bulk download"
                )

                # Update progress for bulk applied
                with self.lock:
                    self.progress["enhanced"] += bulk_applied
                    self.progress["processed"] += bulk_applied

            except Exception as e:
                logger.warning(f"GraphQL bulk download failed for {owner}/{repo}: {e}")
                logger.info("Falling back to REST API for all PRs")

        # STEP 2: Use REST API for remaining PRs (or all PRs if small repo)
        remaining_prs = [pr for pr in prs_to_enhance if not pr.get("close_actor")]

        if remaining_prs:
            strategy_desc = f"REST API enhancement for {len(remaining_prs)} {'remaining' if use_graphql else ''} PRs"
            logger.info(f"🔄 STEP 2: {strategy_desc}")

            # Headers for REST API
            headers = {
                "Authorization": f"Bearer {config.GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
            }

            # Process PRs concurrently in small batches
            batch_size = self.max_workers
            for i in range(0, len(remaining_prs), batch_size):
                # Check for cancellation
                if (
                    self.progress["status"] in ["running", "stopping"]
                    and not self.is_running
                ):
                    logger.info(
                        f"Enhancement stopped during PR processing in {owner}/{repo}"
                    )
                    break

                batch = remaining_prs[i : i + batch_size]
                batch_results = self._process_pr_batch_concurrent(
                    batch, owner, repo, headers
                )

                # Update progress in thread-safe manner
                with self.lock:
                    for success in batch_results:
                        if success:
                            enhanced_count += 1
                            self.progress["enhanced"] += 1
                        else:
                            self.progress["failed"] += 1
                        self.progress["processed"] += 1

                # Conservative delay between batches to respect GitHub API limits
                time.sleep(0.5)
        else:
            if use_graphql:
                logger.info(
                    "🎯 All PRs covered by GraphQL bulk download - no REST API needed!"
                )

        logger.info(f"✅ Total enhanced in {owner}/{repo}: {enhanced_count} PRs")
        return enhanced_count

    def _process_pr_batch_concurrent(
        self, prs_batch: List[Dict], owner: str, repo: str, headers: Dict
    ) -> List[bool]:
        """Process a batch of PRs concurrently."""
        results = []

        with ThreadPoolExecutor(
            max_workers=min(self.max_workers, len(prs_batch))
        ) as executor:
            # Submit all PRs in the batch
            future_to_pr = {
                executor.submit(
                    self._get_close_actor_for_pr_optimized, pr, owner, repo, headers
                ): pr
                for pr in prs_batch
            }

            # Collect results as they complete
            for future in as_completed(future_to_pr):
                try:
                    success = future.result()
                    results.append(success)
                except Exception as e:
                    pr = future_to_pr[future]
                    logger.debug(
                        f"Failed to process PR {pr.get('number', 'unknown')}: {e}"
                    )
                    results.append(False)

        return results

    def _get_bulk_close_actors_graphql(
        self, owner: str, repo: str, headers: Dict, pr_type: str = "merged"
    ) -> Dict[int, str]:
        """Get close_actor data for many PRs at once using GraphQL."""
        query = """
        query($owner: String!, $repo: String!, $first: Int!, $after: String, $states: [PullRequestState!]) {
            repository(owner: $owner, name: $repo) {
                pullRequests(first: $first, after: $after, states: $states, orderBy: {field: UPDATED_AT, direction: DESC}) {
                    pageInfo {
                        hasNextPage
                        endCursor
                    }
                    nodes {
                        number
                        state
                        closedBy: timelineItems(first: 10, itemTypes: [CLOSED_EVENT]) {
                            nodes {
                                ... on ClosedEvent {
                                    actor {
                                        login
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        variables = {
            "owner": owner,
            "repo": repo,
            "first": 100,  # Get 100 PRs per request
            "states": ["MERGED" if pr_type == "merged" else "CLOSED"],
        }

        close_actors = {}
        has_next_page = True
        cursor = None

        while has_next_page:
            if cursor:
                variables["after"] = cursor

            try:
                self._respect_rate_limit()
                response = self.session.post(
                    "https://api.github.com/graphql",
                    headers=headers,
                    json={"query": query, "variables": variables},
                    timeout=30,
                )

                if response.status_code != 200:
                    logger.warning(
                        f"GraphQL request failed for {owner}/{repo}: {response.status_code}"
                    )
                    break

                data = response.json()
                if "errors" in data:
                    logger.warning(
                        f"GraphQL errors for {owner}/{repo}: {data['errors']}"
                    )
                    break

                if not data.get("data", {}).get("repository", {}).get("pullRequests"):
                    break

                pr_data = data["data"]["repository"]["pullRequests"]

                # Process PRs from this page
                for pr in pr_data["nodes"]:
                    pr_number = pr["number"]

                    # Look for close actor in timeline items
                    close_actor = None
                    for item in pr["closedBy"]["nodes"]:
                        if item.get("actor") and item["actor"].get("login"):
                            close_actor = item["actor"]["login"]
                            break

                    if close_actor:
                        close_actors[pr_number] = close_actor

                # Check for next page
                page_info = pr_data["pageInfo"]
                has_next_page = page_info["hasNextPage"]
                cursor = page_info["endCursor"]

                logger.info(
                    f"GraphQL: Got {len(pr_data['nodes'])} PRs from {owner}/{repo}, total close_actors: {len(close_actors)}"
                )

            except Exception as e:
                logger.warning(f"GraphQL request failed for {owner}/{repo}: {e}")
                break

        return close_actors

    def test_hybrid_approach(
        self,
        repo_owner: str = "redhatinsights",
        repo_name: str = "insights-rbac",
        pr_type: str = "merged",
    ) -> Dict[str, Any]:
        """Test the hybrid GraphQL + REST approach on a single repository."""
        try:
            logger.info(
                f"🧪 Testing hybrid approach on {repo_owner}/{repo_name} ({pr_type} PRs)"
            )

            # Setup headers for GraphQL
            graphql_headers = {
                "Authorization": f"Bearer {config.GITHUB_TOKEN}",
                "Content-Type": "application/json",
            }

            # Step 1: GraphQL bulk download
            logger.info("📊 Step 1: GraphQL bulk download...")
            start_time = time.time()
            bulk_close_actors = self._get_bulk_close_actors_graphql(
                repo_owner, repo_name, graphql_headers, pr_type
            )
            graphql_time = time.time() - start_time

            logger.info(
                f"✅ GraphQL: Got {len(bulk_close_actors)} close_actors in {graphql_time:.2f}s"
            )

            # Step 2: Load existing data to compare
            filename = (
                "github_merged_pr_list.json"
                if pr_type == "merged"
                else "github_closed_pr_list.json"
            )
            file_path = Path("data") / filename

            if not file_path.exists():
                return {"error": f"File {filename} not found"}

            data = load_json_data(file_path)

            # Try different key formats to find the repository data
            possible_keys = [
                f"{repo_owner}/{repo_name}",  # owner/repo
                repo_name,  # just repo name
                f"{repo_owner.lower()}/{repo_name}",  # lowercase owner
                repo_name.lower(),  # lowercase repo name
            ]

            existing_prs = []
            for key in possible_keys:
                if key in data.get("data", {}):
                    existing_prs = data["data"][key]
                    break

            if not existing_prs:
                available_keys = list(data.get("data", {}).keys())
                return {
                    "error": f"No PRs found for {repo_owner}/{repo_name}. Available keys: {available_keys[:10]}"
                }

            logger.info(f"📋 Found {len(existing_prs)} existing PRs in data")

            # Step 3: Analyze coverage
            prs_needing_enhancement = [
                pr for pr in existing_prs if not pr.get("close_actor")
            ]
            covered_by_graphql = 0
            still_missing = []

            for pr in prs_needing_enhancement:
                pr_number = pr.get("number")
                if pr_number and pr_number in bulk_close_actors:
                    covered_by_graphql += 1
                else:
                    still_missing.append(pr_number)

            # Step 4: Calculate efficiency metrics
            total_needing = len(prs_needing_enhancement)
            graphql_coverage = (
                (covered_by_graphql / total_needing * 100) if total_needing > 0 else 0
            )
            rest_api_needed = len(still_missing)

            return {
                "success": True,
                "repo": f"{repo_owner}/{repo_name}",
                "pr_type": pr_type,
                "metrics": {
                    "total_prs": len(existing_prs),
                    "needing_enhancement": total_needing,
                    "graphql_covered": covered_by_graphql,
                    "graphql_coverage_pct": round(graphql_coverage, 1),
                    "rest_api_needed": rest_api_needed,
                    "graphql_time_sec": round(graphql_time, 2),
                    "efficiency_gain": f"{covered_by_graphql}x faster (GraphQL vs REST)",
                },
                "sample_missing": still_missing[:10],  # First 10 missing PRs
            }

        except Exception as e:
            logger.error(f"Hybrid approach test failed: {e}")
            return {"error": str(e)}

    def get_missing_close_actor_prs(self) -> Dict[str, Any]:
        """Get all PRs that are missing close_actor data for manual update."""
        try:
            missing_prs = []

            # Check merged PRs
            merged_file = Path("data/github_merged_pr_list.json")
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        if not pr.get("close_actor"):
                            missing_prs.append(
                                {
                                    "repository": repo_name,
                                    "pr_number": pr.get("number"),
                                    "title": pr.get("title", "N/A"),
                                    "url": pr.get("html_url", ""),
                                    "state": "merged",
                                    "created_at": pr.get("created_at", ""),
                                    "closed_at": pr.get("closed_at", ""),
                                    "file": "merged",
                                }
                            )

            # Check closed PRs
            closed_file = Path("data/github_closed_pr_list.json")
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        if not pr.get("close_actor"):
                            missing_prs.append(
                                {
                                    "repository": repo_name,
                                    "pr_number": pr.get("number"),
                                    "title": pr.get("title", "N/A"),
                                    "url": pr.get("html_url", ""),
                                    "state": "closed",
                                    "created_at": pr.get("created_at", ""),
                                    "closed_at": pr.get("closed_at", ""),
                                    "file": "closed",
                                }
                            )

            # Sort by repository, then PR number
            missing_prs.sort(key=lambda x: (x["repository"], x["pr_number"]))

            return {
                "success": True,
                "count": len(missing_prs),
                "missing_prs": missing_prs,
            }

        except Exception as e:
            logger.error(f"Failed to get missing PRs: {e}")
            return {"error": str(e)}

    def manual_update_close_actor(self, updates: List[Dict]) -> Dict[str, Any]:
        """
        Manually update close_actor for specific PRs.

        updates format: [
            {
                "repository": "repo-name",
                "pr_number": 123,
                "close_actor": "username",
                "file": "merged" or "closed"
            }
        ]
        """
        try:
            results = {"updated": 0, "failed": 0, "errors": []}

            # Group updates by file type
            merged_updates = [u for u in updates if u.get("file") == "merged"]
            closed_updates = [u for u in updates if u.get("file") == "closed"]

            # Update merged PRs
            if merged_updates:
                merged_file = Path("data/github_merged_pr_list.json")
                if merged_file.exists():
                    data = load_json_data(merged_file)

                    for update in merged_updates:
                        try:
                            repo_name = update.get("repository")
                            pr_number = update.get("pr_number")
                            close_actor = update.get("close_actor", "").strip()

                            if not all([repo_name, pr_number, close_actor]):
                                results["failed"] += 1
                                results["errors"].append(
                                    f"Invalid update data: {update}"
                                )
                                continue

                            # Find and update the PR
                            repo_prs = data.get("data", {}).get(repo_name, [])
                            pr_found = False

                            for pr in repo_prs:
                                if pr.get("number") == pr_number:
                                    pr["close_actor"] = close_actor
                                    pr_found = True
                                    results["updated"] += 1
                                    logger.info(
                                        f"Manually updated {repo_name}#{pr_number} close_actor: {close_actor}"
                                    )
                                    break

                            if not pr_found:
                                results["failed"] += 1
                                results["errors"].append(
                                    f"PR not found: {repo_name}#{pr_number}"
                                )

                        except Exception as e:
                            results["failed"] += 1
                            results["errors"].append(
                                f"Error updating {update}: {str(e)}"
                            )

                    # Save updated data
                    save_json_data_and_return(data, merged_file)

            # Update closed PRs
            if closed_updates:
                closed_file = Path("data/github_closed_pr_list.json")
                if closed_file.exists():
                    data = load_json_data(closed_file)

                    for update in closed_updates:
                        try:
                            repo_name = update.get("repository")
                            pr_number = update.get("pr_number")
                            close_actor = update.get("close_actor", "").strip()

                            if not all([repo_name, pr_number, close_actor]):
                                results["failed"] += 1
                                results["errors"].append(
                                    f"Invalid update data: {update}"
                                )
                                continue

                            # Find and update the PR
                            repo_prs = data.get("data", {}).get(repo_name, [])
                            pr_found = False

                            for pr in repo_prs:
                                if pr.get("number") == pr_number:
                                    pr["close_actor"] = close_actor
                                    pr_found = True
                                    results["updated"] += 1
                                    logger.info(
                                        f"Manually updated {repo_name}#{pr_number} close_actor: {close_actor}"
                                    )
                                    break

                            if not pr_found:
                                results["failed"] += 1
                                results["errors"].append(
                                    f"PR not found: {repo_name}#{pr_number}"
                                )

                        except Exception as e:
                            results["failed"] += 1
                            results["errors"].append(
                                f"Error updating {update}: {str(e)}"
                            )

                    # Save updated data
                    save_json_data_and_return(data, closed_file)

            success_msg = f"Manual update completed: {results['updated']} updated, {results['failed']} failed"
            logger.info(success_msg)

            return {"success": True, "message": success_msg, "results": results}

        except Exception as e:
            logger.error(f"Manual update failed: {e}")
            return {"error": str(e)}

    def _get_monthly_activity_data(
        self,
        github_username: str,
        gitlab_username: str,
        split_by_konflux: bool = False,
        konflux_only: bool = False,
    ):
        """Get 12-month rolling monthly activity data, independent of date filters.

        Args:
            github_username: GitHub username to filter by
            gitlab_username: GitLab username to filter by
            split_by_konflux: If True, returns {month: {konflux: count, regular: count, total: count}}
            konflux_only: If True, only counts PRs authored by Konflux bots (returns simple counts)
        """
        from datetime import datetime, date, timedelta
        from collections import defaultdict

        if split_by_konflux:
            # Return detailed breakdown: {month: {konflux: count, regular: count, total: count}}
            monthly_activity = defaultdict(
                lambda: {"konflux": 0, "regular": 0, "total": 0}
            )
        else:
            # Return simple count (backward compatibility)
            monthly_activity = defaultdict(int)

        # Calculate 12-month rolling window
        current_date = date.today()
        twelve_months_ago = current_date - timedelta(days=365)
        rolling_date_from = twelve_months_ago.strftime("%Y-%m-%d")
        rolling_date_to = current_date.strftime("%Y-%m-%d")

        # Collect from merged PRs
        merged_file = Path("data/github_merged_pr_list.json")
        if merged_file.exists():
            data = load_json_data(merged_file)
            for repo_name, prs in data.get("data", {}).items():
                for pr in prs:
                    close_actor = pr.get("close_actor")
                    if close_actor in [github_username, gitlab_username]:
                        merged_at = pr.get("merged_at")
                        if merged_at:
                            try:
                                dt = datetime.fromisoformat(
                                    merged_at.replace("Z", "+00:00")
                                )
                                merged_date = dt.strftime("%Y-%m-%d")
                                if rolling_date_from <= merged_date <= rolling_date_to:
                                    month_key = f"{dt.year}-{dt.month:02d}"

                                    if split_by_konflux:
                                        # Check if author is Konflux
                                        author = pr.get("user_login")
                                        is_konflux = (
                                            author and "konflux" in author.lower()
                                        )

                                        if is_konflux:
                                            monthly_activity[month_key]["konflux"] += 1
                                        else:
                                            monthly_activity[month_key]["regular"] += 1
                                        monthly_activity[month_key]["total"] += 1
                                    elif konflux_only:
                                        # Only count if author is Konflux
                                        author = pr.get("user_login")
                                        if author and "konflux" in author.lower():
                                            monthly_activity[month_key] += 1
                                    else:
                                        monthly_activity[month_key] += 1
                            except (ValueError, TypeError):
                                pass

        # Collect from closed PRs
        closed_file = Path("data/github_closed_pr_list.json")
        if closed_file.exists():
            data = load_json_data(closed_file)
            for repo_name, prs in data.get("data", {}).items():
                for pr in prs:
                    close_actor = pr.get("close_actor")
                    if close_actor in [github_username, gitlab_username]:
                        closed_at = pr.get("closed_at")
                        if closed_at:
                            try:
                                dt = datetime.fromisoformat(
                                    closed_at.replace("Z", "+00:00")
                                )
                                closed_date = dt.strftime("%Y-%m-%d")
                                if rolling_date_from <= closed_date <= rolling_date_to:
                                    month_key = f"{dt.year}-{dt.month:02d}"

                                    if split_by_konflux:
                                        # Check if author is Konflux
                                        author = pr.get("user_login")
                                        is_konflux = (
                                            author and "konflux" in author.lower()
                                        )

                                        if is_konflux:
                                            monthly_activity[month_key]["konflux"] += 1
                                        else:
                                            monthly_activity[month_key]["regular"] += 1
                                        monthly_activity[month_key]["total"] += 1
                                    elif konflux_only:
                                        # Only count if author is Konflux
                                        author = pr.get("user_login")
                                        if author and "konflux" in author.lower():
                                            monthly_activity[month_key] += 1
                                    else:
                                        monthly_activity[month_key] += 1
                            except (ValueError, TypeError):
                                pass

        return monthly_activity

    def get_personal_close_actor_stats(
        self, date_from: str = None, date_to: str = None
    ) -> Dict[str, Any]:
        """Get personal close_actor statistics for the current user."""
        try:
            import config
            from datetime import datetime, date
            from collections import defaultdict, Counter
            import calendar

            # Get user's GitHub and GitLab usernames
            github_username = getattr(config, "GITHUB_USERNAME", None) or getattr(
                config, "GITHUB_USER", None
            )
            gitlab_username = getattr(config, "GITLAB_USERNAME", None) or getattr(
                config, "GITLAB_USER", None
            )

            if not github_username and not gitlab_username:
                return {"error": "No GitHub or GitLab username configured"}

            # Load PR data
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            user_closed_merged = 0
            user_closed_closed = 0
            repo_activity = defaultdict(int)
            total_merged = 0
            total_closed = 0
            all_closers = Counter()

            # Get 12-month rolling monthly activity data (independent of date filters, split by Konflux)
            monthly_activity = self._get_monthly_activity_data(
                github_username, gitlab_username, split_by_konflux=True
            )

            # Analyze merged PRs (exclude Konflux PRs)
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        # Skip if authored by Konflux
                        author = pr.get("user_login")
                        if author and "konflux" in author.lower():
                            continue
                        # Apply date range filter to total count as well
                        merged_at = pr.get("merged_at")
                        if date_from or date_to:
                            if merged_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without merged_at when date filtering is requested

                        total_merged += 1
                        close_actor = pr.get("close_actor")
                        if close_actor:
                            all_closers[close_actor] += 1
                        if close_actor in [github_username, gitlab_username]:
                            # For MERGED PRs, filter by merged_at date for stats
                            merged_at = pr.get("merged_at")
                            if merged_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter for main stats ONLY if provided
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue

                                    # Count this closure for main stats
                                    user_closed_merged += 1
                                    repo_activity[repo_name] += 1
                                except (ValueError, TypeError):
                                    # If date parsing fails but no date filter, still count it
                                    if not date_from and not date_to:
                                        user_closed_merged += 1
                                        repo_activity[repo_name] += 1
                            else:
                                # If no merged_at date but no date filter, still count it
                                if not date_from and not date_to:
                                    user_closed_merged += 1
                                    repo_activity[repo_name] += 1

            # Analyze closed PRs (exclude Konflux PRs)
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        # Skip if authored by Konflux
                        author = pr.get("user_login")
                        if author and "konflux" in author.lower():
                            continue
                        # Apply date range filter to total count as well
                        closed_at = pr.get("closed_at")
                        if date_from or date_to:
                            if closed_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= closed_date <= date_to):
                                            continue
                                    elif date_from:
                                        if closed_date < date_from:
                                            continue
                                    elif date_to:
                                        if closed_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without closed_at when date filtering is requested

                        total_closed += 1
                        close_actor = pr.get("close_actor")
                        if close_actor:
                            all_closers[close_actor] += 1
                            if close_actor in [github_username, gitlab_username]:
                                # Extract and check date for filtering
                                closed_at = pr.get("closed_at")
                                if closed_at:
                                    try:
                                        # Parse ISO date
                                        dt = datetime.fromisoformat(
                                            closed_at.replace("Z", "+00:00")
                                        )
                                        closed_date = dt.strftime("%Y-%m-%d")

                                        # Apply date range filter for main stats ONLY if provided
                                        if date_from and date_to:
                                            if not (
                                                date_from <= closed_date <= date_to
                                            ):
                                                continue
                                        elif date_from:
                                            if closed_date < date_from:
                                                continue
                                        elif date_to:
                                            if closed_date > date_to:
                                                continue

                                        # Count this closure for main stats
                                        user_closed_closed += 1
                                        repo_activity[repo_name] += 1
                                    except (ValueError, TypeError):
                                        # If date parsing fails but no date filter, still count it
                                        if not date_from and not date_to:
                                            user_closed_closed += 1
                                            repo_activity[repo_name] += 1
                                else:
                                    # If no closed_at date but no date filter, still count it
                                    if not date_from and not date_to:
                                        user_closed_closed += 1
                                        repo_activity[repo_name] += 1

            # Calculate user ranking
            user_total = user_closed_merged + user_closed_closed
            user_rank = 1
            for closer, count in all_closers.most_common():
                if closer in [github_username, gitlab_username]:
                    break
                user_rank += 1

            # Prepare monthly activity data (last 12 months)
            current_date = date.today()
            monthly_data = []
            for i in range(11, -1, -1):  # Last 12 months
                year = current_date.year
                month = current_date.month - i
                if month <= 0:
                    month += 12
                    year -= 1

                month_key = f"{year}-{month:02d}"
                month_name = calendar.month_abbr[month]
                month_data = monthly_activity.get(
                    month_key, {"konflux": 0, "regular": 0, "total": 0}
                )
                monthly_data.append(
                    {
                        "month": f"{month_name} {year}",
                        "count": month_data["total"],
                        "konflux": month_data["konflux"],
                        "regular": month_data["regular"],
                    }
                )

            # Top repositories - convert defaultdict to Counter for most_common
            repo_counter = Counter(repo_activity)
            top_repos = dict(repo_counter.most_common(5))

            return {
                "success": True,
                "username": github_username or gitlab_username,
                "stats": {
                    "merged_prs_closed": user_closed_merged,
                    "closed_prs_closed": user_closed_closed,
                    "total_closed": user_total,
                    "rank": user_rank,
                    "total_users": len(all_closers),
                    "percentile": round((1 - (user_rank - 1) / len(all_closers)) * 100)
                    if all_closers
                    else 0,
                },
                "monthly_activity": monthly_data,
                "top_repositories": top_repos,
                "total_prs_in_system": total_merged + total_closed,
            }

        except Exception as e:
            logger.error(f"Failed to get personal close_actor stats: {e}")
            return {"error": str(e)}

    def get_personal_konflux_close_actor_stats(
        self, date_from: str = None, date_to: str = None
    ) -> Dict[str, Any]:
        """Get personal close_actor statistics filtered for PRs authored by Konflux bots."""
        try:
            import config
            from datetime import datetime, date
            from collections import defaultdict, Counter
            import calendar

            # Get user's GitHub and GitLab usernames
            github_username = getattr(config, "GITHUB_USERNAME", None) or getattr(
                config, "GITHUB_USER", None
            )
            gitlab_username = getattr(config, "GITLAB_USERNAME", None) or getattr(
                config, "GITLAB_USER", None
            )

            if not github_username and not gitlab_username:
                return {"error": "No GitHub or GitLab username configured"}

            # Load PR data
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            user_closed_merged = 0
            user_closed_closed = 0
            repo_activity = defaultdict(int)
            total_merged = 0
            total_closed = 0

            # Get 12-month rolling monthly activity data (independent of date filters, Konflux-filtered)
            # Note: For Konflux method, we filter to only Konflux PRs and return simple counts
            monthly_activity = self._get_monthly_activity_data(
                github_username,
                gitlab_username,
                split_by_konflux=False,
                konflux_only=True,
            )

            # Analyze merged PRs - filter for Konflux authors
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        author = pr.get("user_login")

                        # Skip if not authored by Konflux
                        if not author or "konflux" not in author.lower():
                            continue

                        # Apply date range filter to total count as well
                        merged_at = pr.get("merged_at")
                        if date_from or date_to:
                            if merged_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without merged_at when date filtering is requested

                        total_merged += 1

                        if close_actor in [github_username, gitlab_username]:
                            merged_at = pr.get("merged_at")
                            if merged_at:
                                try:
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # PR already passed date filtering above, count for main stats
                                    user_closed_merged += 1
                                    repo_activity[repo_name] += 1
                                except (ValueError, TypeError):
                                    # Still count for main stats if date parsing fails
                                    user_closed_merged += 1
                                    repo_activity[repo_name] += 1
                            else:
                                # No date available, still count for main stats
                                user_closed_merged += 1
                                repo_activity[repo_name] += 1

            # Analyze closed PRs - filter for Konflux authors
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        author = pr.get("user_login")

                        # Skip if not authored by Konflux
                        if not author or "konflux" not in author.lower():
                            continue

                        # Apply date range filter to total count as well
                        closed_at = pr.get("closed_at")
                        if date_from or date_to:
                            if closed_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= closed_date <= date_to):
                                            continue
                                    elif date_from:
                                        if closed_date < date_from:
                                            continue
                                    elif date_to:
                                        if closed_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without closed_at when date filtering is requested

                        total_closed += 1

                        if close_actor in [github_username, gitlab_username]:
                            closed_at = pr.get("closed_at")
                            if closed_at:
                                try:
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # PR already passed date filtering above, count for main stats
                                    user_closed_closed += 1
                                    repo_activity[repo_name] += 1
                                except (ValueError, TypeError):
                                    # Still count for main stats if date parsing fails
                                    user_closed_closed += 1
                                    repo_activity[repo_name] += 1
                            else:
                                # No date available, still count for main stats
                                user_closed_closed += 1
                                repo_activity[repo_name] += 1

            # Prepare monthly activity data (last 12 months)
            current_date = date.today()
            monthly_data = []
            for i in range(11, -1, -1):  # Last 12 months
                year = current_date.year
                month = current_date.month - i
                if month <= 0:
                    month += 12
                    year -= 1

                month_key = f"{year}-{month:02d}"
                month_name = calendar.month_abbr[month]
                monthly_data.append(
                    {
                        "month": f"{month_name} {year}",
                        "count": monthly_activity.get(month_key, 0),
                    }
                )

            # Top repositories - convert defaultdict to Counter for most_common
            repo_counter = Counter(repo_activity)
            top_repos = dict(repo_counter.most_common(5))

            user_total = user_closed_merged + user_closed_closed

            return {
                "success": True,
                "username": github_username or gitlab_username,
                "stats": {
                    "merged_prs_closed": user_closed_merged,
                    "closed_prs_closed": user_closed_closed,
                    "total_closed": user_total,
                },
                "monthly_activity": monthly_data,
                "top_repositories": top_repos,
                "total_konflux_prs_in_system": total_merged + total_closed,
            }

        except Exception as e:
            logger.error(f"Failed to get personal Konflux close_actor stats: {e}")
            return {"error": str(e)}

    def get_team_close_actor_stats(
        self, date_from: str = None, date_to: str = None
    ) -> Dict[str, Any]:
        """Get team-wide close_actor statistics (similar to personal but for all users).

        Note: Personal repositories are excluded from team statistics.
        """
        try:
            from datetime import datetime, date
            from collections import defaultdict, Counter
            import calendar
            import config

            # Load PR data
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            # Get GitHub username for personal repo filtering
            github_username = getattr(config, "GITHUB_USERNAME", None)

            team_closed_merged = 0
            team_closed_closed = 0
            repo_activity = defaultdict(int)
            total_merged = 0
            total_closed = 0
            all_closers = Counter()

            # Get 12-month rolling monthly activity data (independent of date filters, split by Konflux)
            # For team stats, we aggregate all users' activity with Konflux split for monthly chart
            monthly_activity = self._get_team_monthly_activity_data()

            # Analyze merged PRs
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        # Apply date range filter to total count
                        merged_at = pr.get("merged_at")
                        if date_from or date_to:
                            if merged_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without merged_at when date filtering is requested

                        # Skip PRs authored by Konflux bots (we want only non-Konflux data)
                        author = pr.get("user_login")
                        if author and "konflux" in author.lower():
                            continue

                        # Skip PRs from personal repositories
                        if github_username:
                            html_url = pr.get("html_url", "")
                            if html_url and "github.com" in html_url:
                                # Extract owner from URL: https://github.com/owner/repo/pull/123
                                url_parts = html_url.split("/")
                                if len(url_parts) >= 5:
                                    owner = url_parts[
                                        3
                                    ]  # github.com is index 2, owner is index 3
                                    if owner.lower() == github_username.lower():
                                        continue

                        total_merged += 1
                        close_actor = pr.get("close_actor")
                        if close_actor:
                            all_closers[close_actor] += 1
                            # Count this closure for team stats
                            team_closed_merged += 1
                            repo_activity[repo_name] += 1

            # Analyze closed PRs
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        # Apply date range filter to total count
                        closed_at = pr.get("closed_at")
                        if date_from or date_to:
                            if closed_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= closed_date <= date_to):
                                            continue
                                    elif date_from:
                                        if closed_date < date_from:
                                            continue
                                    elif date_to:
                                        if closed_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without closed_at when date filtering is requested

                        # Skip PRs authored by Konflux bots (we want only non-Konflux data)
                        author = pr.get("user_login")
                        if author and "konflux" in author.lower():
                            continue

                        # Skip PRs from personal repositories
                        if github_username:
                            html_url = pr.get("html_url", "")
                            if html_url and "github.com" in html_url:
                                # Extract owner from URL: https://github.com/owner/repo/pull/123
                                url_parts = html_url.split("/")
                                if len(url_parts) >= 5:
                                    owner = url_parts[
                                        3
                                    ]  # github.com is index 2, owner is index 3
                                    if owner.lower() == github_username.lower():
                                        continue

                        total_closed += 1
                        close_actor = pr.get("close_actor")
                        if close_actor:
                            all_closers[close_actor] += 1
                            # Count this closure for team stats
                            team_closed_closed += 1
                            repo_activity[repo_name] += 1

            # Prepare monthly activity data (last 12 months)
            current_date = date.today()
            monthly_data = []
            for i in range(11, -1, -1):  # Last 12 months
                year = current_date.year
                month = current_date.month - i
                if month <= 0:
                    month += 12
                    year -= 1

                month_key = f"{year}-{month:02d}"
                month_name = calendar.month_abbr[month]

                # Monthly activity has split data structure
                month_data = monthly_activity.get(
                    month_key, {"konflux": 0, "regular": 0, "total": 0}
                )
                monthly_data.append(
                    {
                        "month": f"{month_name} {year}",
                        "count": month_data["total"],
                        "konflux": month_data["konflux"],
                        "regular": month_data["regular"],
                    }
                )

            # Top repositories - convert defaultdict to Counter for most_common
            repo_counter = Counter(repo_activity)
            top_repos = dict(repo_counter.most_common(5))

            # Top close actors - get top 5
            top_closers = dict(all_closers.most_common(5))

            return {
                "success": True,
                "stats": {
                    "merged_prs_closed": team_closed_merged,
                    "closed_prs_closed": team_closed_closed,
                    "total_closed": team_closed_merged + team_closed_closed,
                },
                "monthly_activity": monthly_data,
                "top_repositories": top_repos,
                "top_closers": top_closers,
            }

        except Exception as e:
            logger.error(f"Failed to get team close_actor stats: {e}")
            return {"error": str(e)}

    def get_team_konflux_close_actor_stats(
        self, date_from: str = None, date_to: str = None
    ) -> Dict[str, Any]:
        """Get team-wide close_actor statistics filtered for PRs authored by Konflux bots.

        Note: Personal repositories are excluded from team statistics.
        """
        try:
            from datetime import datetime, date
            from collections import defaultdict, Counter
            import calendar
            import config

            # Load PR data
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            # Get GitHub username for personal repo filtering
            github_username = getattr(config, "GITHUB_USERNAME", None)

            team_closed_merged = 0
            team_closed_closed = 0
            repo_activity = defaultdict(int)
            all_closers = Counter()  # Track who closed Konflux PRs
            total_merged = 0
            total_closed = 0

            # Get 12-month rolling monthly activity data (independent of date filters, Konflux-filtered)
            monthly_activity = self._get_team_monthly_activity_data(konflux_only=True)

            # Analyze merged PRs - filter for Konflux authors
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        author = pr.get("user_login")

                        # Skip if not authored by Konflux
                        if not author or "konflux" not in author.lower():
                            continue

                        # Apply date range filter to total count
                        merged_at = pr.get("merged_at")
                        if date_from or date_to:
                            if merged_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without merged_at when date filtering is requested

                        # Skip PRs from personal repositories
                        if github_username:
                            html_url = pr.get("html_url", "")
                            if html_url and "github.com" in html_url:
                                # Extract owner from URL: https://github.com/owner/repo/pull/123
                                url_parts = html_url.split("/")
                                if len(url_parts) >= 5:
                                    owner = url_parts[
                                        3
                                    ]  # github.com is index 2, owner is index 3
                                    if owner.lower() == github_username.lower():
                                        continue

                        total_merged += 1

                        if close_actor:
                            all_closers[close_actor] += (
                                1  # Track who closed this Konflux PR
                            )
                            team_closed_merged += 1
                            repo_activity[repo_name] += 1

            # Analyze closed PRs - filter for Konflux authors
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        author = pr.get("user_login")

                        # Skip if not authored by Konflux
                        if not author or "konflux" not in author.lower():
                            continue

                        # Apply date range filter to total count
                        closed_at = pr.get("closed_at")
                        if date_from or date_to:
                            if closed_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= closed_date <= date_to):
                                            continue
                                    elif date_from:
                                        if closed_date < date_from:
                                            continue
                                    elif date_to:
                                        if closed_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without closed_at when date filtering is requested

                        # Skip PRs from personal repositories
                        if github_username:
                            html_url = pr.get("html_url", "")
                            if html_url and "github.com" in html_url:
                                # Extract owner from URL: https://github.com/owner/repo/pull/123
                                url_parts = html_url.split("/")
                                if len(url_parts) >= 5:
                                    owner = url_parts[
                                        3
                                    ]  # github.com is index 2, owner is index 3
                                    if owner.lower() == github_username.lower():
                                        continue

                        total_closed += 1

                        if close_actor:
                            all_closers[close_actor] += (
                                1  # Track who closed this Konflux PR
                            )
                            team_closed_closed += 1
                            repo_activity[repo_name] += 1

            # Prepare monthly activity data (last 12 months)
            current_date = date.today()
            monthly_data = []
            for i in range(11, -1, -1):  # Last 12 months
                year = current_date.year
                month = current_date.month - i
                if month <= 0:
                    month += 12
                    year -= 1

                month_key = f"{year}-{month:02d}"
                month_name = calendar.month_abbr[month]
                monthly_data.append(
                    {
                        "month": f"{month_name} {year}",
                        "count": monthly_activity.get(month_key, 0),
                    }
                )

            # Top repositories - convert defaultdict to Counter for most_common
            repo_counter = Counter(repo_activity)
            top_repos = dict(repo_counter.most_common(5))

            # Top close actors - get top 5
            top_closers = dict(all_closers.most_common(5))

            team_total = team_closed_merged + team_closed_closed

            return {
                "success": True,
                "stats": {
                    "merged_prs_closed": team_closed_merged,
                    "closed_prs_closed": team_closed_closed,
                    "total_closed": team_total,
                },
                "monthly_activity": monthly_data,
                "top_repositories": top_repos,
                "top_closers": top_closers,
            }

        except Exception as e:
            logger.error(f"Failed to get team Konflux close_actor stats: {e}")
            return {"error": str(e)}

    def get_repository_breakdown(
        self, date_from: str = None, date_to: str = None
    ) -> Dict[str, Any]:
        """Get repository breakdown data for organization statistics."""
        try:
            from datetime import datetime
            from collections import defaultdict, Counter

            # Load PR data
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            repo_stats = defaultdict(lambda: {"total_prs": 0, "closers": Counter()})

            # Analyze merged PRs
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        if not close_actor:
                            continue

                        # Skip PRs authored by Konflux bots (we want only non-Konflux data)
                        author = pr.get("user_login")
                        if author and "konflux" in author.lower():
                            continue

                        # Apply date range filter
                        merged_at = pr.get("merged_at")
                        if date_from or date_to:
                            if merged_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without merged_at when date filtering is requested

                        repo_stats[repo_name]["total_prs"] += 1
                        repo_stats[repo_name]["closers"][close_actor] += 1

            # Analyze closed PRs
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        if not close_actor:
                            continue

                        # Skip PRs authored by Konflux bots (we want only non-Konflux data)
                        author = pr.get("user_login")
                        if author and "konflux" in author.lower():
                            continue

                        # Apply date range filter
                        closed_at = pr.get("closed_at")
                        if date_from or date_to:
                            if closed_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= closed_date <= date_to):
                                            continue
                                    elif date_from:
                                        if closed_date < date_from:
                                            continue
                                    elif date_to:
                                        if closed_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without closed_at when date filtering is requested

                        repo_stats[repo_name]["total_prs"] += 1
                        repo_stats[repo_name]["closers"][close_actor] += 1

            # Convert to the format expected by renderRepositoryBreakdown
            top_repositories = []
            for repo_name, stats in repo_stats.items():
                if stats["total_prs"] > 0:
                    top_closer, top_closer_count = stats["closers"].most_common(1)[0]
                    top_repositories.append(
                        {
                            "repository": repo_name,
                            "total_prs": stats["total_prs"],
                            "unique_closers": len(stats["closers"]),
                            "top_closer": top_closer,
                            "top_closer_count": top_closer_count,
                        }
                    )

            # Sort by total PRs, descending
            top_repositories.sort(key=lambda x: x["total_prs"], reverse=True)

            return {
                "success": True,
                "top_repositories": top_repositories[:20],  # Top 20 repos
            }

        except Exception as e:
            logger.error(f"Failed to get repository breakdown: {e}")
            return {"error": str(e)}

    def get_konflux_repository_breakdown(
        self, date_from: str = None, date_to: str = None
    ) -> Dict[str, Any]:
        """Get repository breakdown data filtered for PRs authored by Konflux bots."""
        try:
            from datetime import datetime
            from collections import defaultdict, Counter

            # Load PR data
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            repo_stats = defaultdict(lambda: {"total_prs": 0, "closers": Counter()})

            # Analyze merged PRs - filter for Konflux authors
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        author = pr.get("user_login")

                        # Skip if not authored by Konflux or no close_actor
                        if (
                            not close_actor
                            or not author
                            or "konflux" not in author.lower()
                        ):
                            continue

                        # Apply date range filter
                        merged_at = pr.get("merged_at")
                        if date_from or date_to:
                            if merged_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without merged_at when date filtering is requested

                        repo_stats[repo_name]["total_prs"] += 1
                        repo_stats[repo_name]["closers"][close_actor] += 1

            # Analyze closed PRs - filter for Konflux authors
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        close_actor = pr.get("close_actor")
                        author = pr.get("user_login")

                        # Skip if not authored by Konflux or no close_actor
                        if (
                            not close_actor
                            or not author
                            or "konflux" not in author.lower()
                        ):
                            continue

                        # Apply date range filter
                        closed_at = pr.get("closed_at")
                        if date_from or date_to:
                            if closed_at:
                                try:
                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= closed_date <= date_to):
                                            continue
                                    elif date_from:
                                        if closed_date < date_from:
                                            continue
                                    elif date_to:
                                        if closed_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without closed_at when date filtering is requested

                        repo_stats[repo_name]["total_prs"] += 1
                        repo_stats[repo_name]["closers"][close_actor] += 1

            # Convert to the format expected by renderRepositoryBreakdown
            top_repositories = []
            for repo_name, stats in repo_stats.items():
                if stats["total_prs"] > 0:
                    top_closer, top_closer_count = stats["closers"].most_common(1)[0]
                    top_repositories.append(
                        {
                            "repository": repo_name,
                            "total_prs": stats["total_prs"],
                            "unique_closers": len(stats["closers"]),
                            "top_closer": top_closer,
                            "top_closer_count": top_closer_count,
                        }
                    )

            # Sort by total PRs, descending
            top_repositories.sort(key=lambda x: x["total_prs"], reverse=True)

            return {
                "success": True,
                "top_repositories": top_repositories[:20],  # Top 20 repos
            }

        except Exception as e:
            logger.error(f"Failed to get Konflux repository breakdown: {e}")
            return {"error": str(e)}

    def _get_team_monthly_activity_data(
        self, konflux_only: bool = False, exclude_konflux: bool = False
    ):
        """Get team-wide 12-month rolling monthly activity data.

        Note: Personal repositories are excluded from team statistics.
        """
        from datetime import datetime, date, timedelta
        from collections import defaultdict
        import config

        # Get GitHub username for personal repo filtering
        github_username = getattr(config, "GITHUB_USERNAME", None)

        if konflux_only:
            # Return simple count for Konflux-only data
            monthly_activity = defaultdict(int)
        elif exclude_konflux:
            # Return simple count for non-Konflux data only
            monthly_activity = defaultdict(int)
        else:
            # Return detailed breakdown: {month: {konflux: count, regular: count, total: count}}
            monthly_activity = defaultdict(
                lambda: {"konflux": 0, "regular": 0, "total": 0}
            )

        # Calculate 12-month rolling window
        current_date = date.today()
        twelve_months_ago = current_date - timedelta(days=365)
        rolling_date_from = twelve_months_ago.strftime("%Y-%m-%d")
        rolling_date_to = current_date.strftime("%Y-%m-%d")

        # Collect from merged PRs
        merged_file = Path("data/github_merged_pr_list.json")
        if merged_file.exists():
            data = load_json_data(merged_file)
            for repo_name, prs in data.get("data", {}).items():
                for pr in prs:
                    # Skip PRs from personal repositories
                    if github_username:
                        html_url = pr.get("html_url", "")
                        if html_url and "github.com" in html_url:
                            # Extract owner from URL: https://github.com/owner/repo/pull/123
                            url_parts = html_url.split("/")
                            if len(url_parts) >= 5:
                                owner = url_parts[3]
                                if owner.lower() == github_username.lower():
                                    continue

                    close_actor = pr.get("close_actor")
                    if close_actor:  # Any user who closed PRs
                        merged_at = pr.get("merged_at")
                        if merged_at:
                            try:
                                dt = datetime.fromisoformat(
                                    merged_at.replace("Z", "+00:00")
                                )
                                merged_date = dt.strftime("%Y-%m-%d")
                                if rolling_date_from <= merged_date <= rolling_date_to:
                                    month_key = f"{dt.year}-{dt.month:02d}"

                                    if konflux_only:
                                        # Only count if author is Konflux
                                        author = pr.get("user_login")
                                        if author and "konflux" in author.lower():
                                            monthly_activity[month_key] += 1
                                    elif exclude_konflux:
                                        # Only count if author is NOT Konflux
                                        author = pr.get("user_login")
                                        if not (author and "konflux" in author.lower()):
                                            monthly_activity[month_key] += 1
                                    else:
                                        # Check if author is Konflux for split data
                                        author = pr.get("user_login")
                                        is_konflux = (
                                            author and "konflux" in author.lower()
                                        )

                                        if is_konflux:
                                            monthly_activity[month_key]["konflux"] += 1
                                        else:
                                            monthly_activity[month_key]["regular"] += 1
                                        monthly_activity[month_key]["total"] += 1
                            except (ValueError, TypeError):
                                pass

        # Collect from closed PRs
        closed_file = Path("data/github_closed_pr_list.json")
        if closed_file.exists():
            data = load_json_data(closed_file)
            for repo_name, prs in data.get("data", {}).items():
                for pr in prs:
                    # Skip PRs from personal repositories
                    if github_username:
                        html_url = pr.get("html_url", "")
                        if html_url and urlparse(html_url).hostname == "github.com":
                            # Extract owner from URL: https://github.com/owner/repo/pull/123
                            url_parts = html_url.split("/")
                            if len(url_parts) >= 5:
                                owner = url_parts[3]
                                if owner.lower() == github_username.lower():
                                    continue

                    close_actor = pr.get("close_actor")
                    if close_actor:  # Any user who closed PRs
                        closed_at = pr.get("closed_at")
                        if closed_at:
                            try:
                                dt = datetime.fromisoformat(
                                    closed_at.replace("Z", "+00:00")
                                )
                                closed_date = dt.strftime("%Y-%m-%d")
                                if rolling_date_from <= closed_date <= rolling_date_to:
                                    month_key = f"{dt.year}-{dt.month:02d}"

                                    if konflux_only:
                                        # Only count if author is Konflux
                                        author = pr.get("user_login")
                                        if author and "konflux" in author.lower():
                                            monthly_activity[month_key] += 1
                                    elif exclude_konflux:
                                        # Only count if author is NOT Konflux
                                        author = pr.get("user_login")
                                        if not (author and "konflux" in author.lower()):
                                            monthly_activity[month_key] += 1
                                    else:
                                        # Check if author is Konflux for split data
                                        author = pr.get("user_login")
                                        is_konflux = (
                                            author and "konflux" in author.lower()
                                        )

                                        if is_konflux:
                                            monthly_activity[month_key]["konflux"] += 1
                                        else:
                                            monthly_activity[month_key]["regular"] += 1
                                        monthly_activity[month_key]["total"] += 1
                            except (ValueError, TypeError):
                                pass

        return monthly_activity

    def get_organization_close_actor_stats(
        self, date_from: str = None, date_to: str = None
    ) -> Dict[str, Any]:
        """Get organization-wide close_actor statistics."""
        try:
            from collections import defaultdict, Counter

            # Load PR data
            merged_file = Path("data/github_merged_pr_list.json")
            closed_file = Path("data/github_closed_pr_list.json")

            all_closers = Counter()
            repo_stats = defaultdict(lambda: {"total": 0, "closers": Counter()})
            self_closes = 0
            cross_closes = 0
            total_prs = 0

            # Analyze merged PRs
            if merged_file.exists():
                data = load_json_data(merged_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        # Apply date range filter if provided (use merged_at for merged PRs)
                        if date_from or date_to:
                            merged_at = pr.get("merged_at")
                            if merged_at:
                                try:
                                    from datetime import datetime

                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        merged_at.replace("Z", "+00:00")
                                    )
                                    merged_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= merged_date <= date_to):
                                            continue
                                    elif date_from:
                                        if merged_date < date_from:
                                            continue
                                    elif date_to:
                                        if merged_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without merged_at when date filtering is requested

                        total_prs += 1
                        repo_stats[repo_name]["total"] += 1

                        close_actor = pr.get("close_actor")
                        author = (
                            pr.get("user", {}).get("login") if pr.get("user") else None
                        )

                        if close_actor:
                            all_closers[close_actor] += 1
                            repo_stats[repo_name]["closers"][close_actor] += 1

                            # Check if self-close vs cross-close
                            if author and close_actor == author:
                                self_closes += 1
                            elif author and close_actor != author:
                                cross_closes += 1

            # Analyze closed PRs
            if closed_file.exists():
                data = load_json_data(closed_file)
                for repo_name, prs in data.get("data", {}).items():
                    for pr in prs:
                        # Apply date range filter if provided
                        if date_from or date_to:
                            closed_at = pr.get("closed_at")
                            if closed_at:
                                try:
                                    from datetime import datetime

                                    # Parse ISO date
                                    dt = datetime.fromisoformat(
                                        closed_at.replace("Z", "+00:00")
                                    )
                                    closed_date = dt.strftime("%Y-%m-%d")

                                    # Apply date range filter
                                    if date_from and date_to:
                                        if not (date_from <= closed_date <= date_to):
                                            continue
                                    elif date_from:
                                        if closed_date < date_from:
                                            continue
                                    elif date_to:
                                        if closed_date > date_to:
                                            continue
                                except (ValueError, TypeError):
                                    continue  # Skip PRs with invalid dates
                            else:
                                continue  # Skip PRs without close_actor date if date filtering is requested

                        total_prs += 1
                        repo_stats[repo_name]["total"] += 1

                        close_actor = pr.get("close_actor")
                        author = (
                            pr.get("user", {}).get("login") if pr.get("user") else None
                        )

                        if close_actor:
                            all_closers[close_actor] += 1
                            repo_stats[repo_name]["closers"][close_actor] += 1

                            # Check if self-close vs cross-close
                            if author and close_actor == author:
                                self_closes += 1
                            elif author and close_actor != author:
                                cross_closes += 1

            # Prepare top closers list
            top_closers = [
                {
                    "username": closer,
                    "count": count,
                    "percentage": round((count / total_prs) * 100, 1),
                }
                for closer, count in all_closers.most_common(10)
            ]

            # Repository breakdown - top 10 most active repos
            top_repos = []
            for repo, stats in sorted(
                repo_stats.items(), key=lambda x: x[1]["total"], reverse=True
            )[:10]:
                top_closer = stats["closers"].most_common(1)
                top_repos.append(
                    {
                        "repository": repo,
                        "total_prs": stats["total"],
                        "unique_closers": len(stats["closers"]),
                        "top_closer": top_closer[0][0] if top_closer else "Unknown",
                        "top_closer_count": top_closer[0][1] if top_closer else 0,
                    }
                )

            # Calculate interesting insights
            total_with_close_actor = sum(all_closers.values())
            cross_close_percentage = (
                round((cross_closes / total_with_close_actor) * 100, 1)
                if total_with_close_actor
                else 0
            )
            self_close_percentage = (
                round((self_closes / total_with_close_actor) * 100, 1)
                if total_with_close_actor
                else 0
            )

            return {
                "success": True,
                "stats": {
                    "total_prs": total_prs,
                    "total_closers": len(all_closers),
                    "self_closes": self_closes,
                    "cross_closes": cross_closes,
                    "self_close_percentage": self_close_percentage,
                    "cross_close_percentage": cross_close_percentage,
                    "avg_prs_per_closer": round(
                        total_with_close_actor / len(all_closers), 1
                    )
                    if all_closers
                    else 0,
                },
                "top_closers": top_closers,
                "top_repositories": top_repos,
                "insights": {
                    "most_collaborative_repo": max(
                        repo_stats.items(), key=lambda x: len(x[1]["closers"])
                    )[0]
                    if repo_stats
                    else "Unknown",
                    "most_active_closer": all_closers.most_common(1)[0][0]
                    if all_closers
                    else "Unknown",
                    "total_repositories": len(repo_stats),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get organization close_actor stats: {e}")
            return {"error": str(e)}

    def _get_close_actor_for_pr(
        self, pr: Dict, owner: str, repo: str, headers: Dict
    ) -> bool:
        """Get close_actor for a single PR using REST API."""
        pr_number = pr.get("number")
        if not pr_number:
            return False

        try:
            # Method 1: Get PR details directly (has closed_by field)
            pr_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
            response = requests.get(pr_url, headers=headers, timeout=30)

            if response.status_code == 200:
                pr_data = response.json()
                if pr_data.get("closed_by") and pr_data["closed_by"].get("login"):
                    pr["close_actor"] = pr_data["closed_by"]["login"]
                    return True

            # Method 2: Get events (fallback)
            time.sleep(0.1)  # Small delay between requests
            events_url = (
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/events"
            )
            response = requests.get(events_url, headers=headers, timeout=30)

            if response.status_code == 200:
                events = response.json()
                for event in events:
                    if (
                        event.get("event") == "closed"
                        and event.get("actor")
                        and event["actor"].get("login")
                    ):
                        pr["close_actor"] = event["actor"]["login"]
                        return True

            # Method 3: Get issues events (final fallback)
            time.sleep(0.1)  # Small delay between requests
            issues_events_url = (
                f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/events"
            )
            response = requests.get(issues_events_url, headers=headers, timeout=30)

            if response.status_code == 200:
                events = response.json()
                for event in events:
                    if (
                        event.get("event") == "closed"
                        and event.get("actor")
                        and event["actor"].get("login")
                    ):
                        pr["close_actor"] = event["actor"]["login"]
                        return True

            # If we get here, we couldn't find close_actor
            pr["close_actor"] = None  # Mark as attempted but not found
            return False

        except Exception as e:
            logger.debug(f"Failed to get close_actor for PR {pr_number}: {e}")
            pr["close_actor"] = None
            return False

    def _respect_rate_limit(self):
        """Implement intelligent rate limiting to respect GitHub API limits."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _handle_api_response(self, response, pr_number: int) -> tuple:
        """Handle API response with proper rate limit and error detection."""
        if response.status_code == 403:
            # Rate limit exceeded
            if "rate limit" in response.text.lower():
                logger.warning(f"Rate limit hit for PR {pr_number}, backing off")
                time.sleep(2.0)  # Back off significantly
                return False, "rate_limit"
        elif response.status_code == 404:
            return False, "not_found"
        elif response.status_code == 422:
            return False, "unprocessable"
        elif response.status_code >= 500:
            return False, "server_error"
        elif response.status_code == 200:
            return True, "success"
        else:
            return False, f"http_{response.status_code}"

    def _get_close_actor_for_pr_optimized(
        self, pr: Dict, owner: str, repo: str, headers: Dict
    ) -> bool:
        """Rate-limited version with better error handling."""
        pr_number = pr.get("number")
        if not pr_number:
            return False

        max_retries = 2
        base_delay = 0.1

        for attempt in range(max_retries + 1):
            try:
                # Respect rate limiting
                self._respect_rate_limit()

                # Method 1: Get PR details directly (has closed_by field)
                pr_url = (
                    f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
                )
                response = self.session.get(pr_url, headers=headers, timeout=20)

                success, status = self._handle_api_response(response, pr_number)
                if success:
                    pr_data = response.json()
                    if pr_data.get("closed_by") and pr_data["closed_by"].get("login"):
                        pr["close_actor"] = pr_data["closed_by"]["login"]
                        return True
                elif status == "rate_limit" and attempt < max_retries:
                    # Exponential backoff for rate limits
                    time.sleep(base_delay * (2**attempt))
                    continue
                elif status in ["not_found", "unprocessable"]:
                    # Don't retry these errors
                    break

                # Method 2: Get events (fallback) with rate limiting
                self._respect_rate_limit()
                events_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/events"
                response = self.session.get(events_url, headers=headers, timeout=20)

                success, status = self._handle_api_response(response, pr_number)
                if success:
                    events = response.json()
                    for event in events:
                        if (
                            event.get("event") == "closed"
                            and event.get("actor")
                            and event["actor"].get("login")
                        ):
                            pr["close_actor"] = event["actor"]["login"]
                            return True
                elif status == "rate_limit" and attempt < max_retries:
                    time.sleep(base_delay * (2**attempt))
                    continue

                # Method 3: Get issues events (final fallback) with rate limiting
                self._respect_rate_limit()
                issues_events_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/events"
                response = self.session.get(
                    issues_events_url, headers=headers, timeout=20
                )

                success, status = self._handle_api_response(response, pr_number)
                if success:
                    events = response.json()
                    for event in events:
                        if (
                            event.get("event") == "closed"
                            and event.get("actor")
                            and event["actor"].get("login")
                        ):
                            pr["close_actor"] = event["actor"]["login"]
                            return True
                elif status == "rate_limit" and attempt < max_retries:
                    time.sleep(base_delay * (2**attempt))
                    continue

                # If we reach here, all methods failed for this attempt
                if attempt < max_retries:
                    time.sleep(base_delay * (2**attempt))
                    continue
                else:
                    break

            except Exception as e:
                logger.debug(f"Attempt {attempt + 1} failed for PR {pr_number}: {e}")
                if attempt < max_retries:
                    time.sleep(base_delay * (2**attempt))
                    continue
                else:
                    break

        # If we get here, all attempts failed
        pr["close_actor"] = None  # Mark as attempted but not found
        return False


# Global instance
enhancer = CloseActorEnhancer()
