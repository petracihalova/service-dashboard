#!/usr/bin/env python3
"""Debug script to check close_actor data for the current user."""

import os
import json
from pathlib import Path
from collections import Counter, defaultdict

# Load environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def load_json_data(file_path):
    """Load JSON data from file."""
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}


def debug_close_actor_data():
    """Debug close_actor data for current user."""

    # Get configured usernames
    github_username = os.environ.get("GITHUB_USERNAME", "")
    gitlab_username = os.environ.get("GITLAB_USERNAME", "")

    print("🔧 === CLOSE ACTOR DEBUG REPORT === 🔧")
    print("📋 Configured usernames:")
    print(f"   GitHub: '{github_username}'")
    print(f"   GitLab: '{gitlab_username}'")
    print()

    if not github_username and not gitlab_username:
        print("❌ ERROR: No usernames configured!")
        return

    # Check merged PRs
    merged_file = Path("data/github_merged_pr_list.json")
    closed_file = Path("data/github_closed_pr_list.json")

    if not merged_file.exists():
        print("❌ ERROR: github_merged_pr_list.json not found!")
        return

    if not closed_file.exists():
        print("❌ ERROR: github_closed_pr_list.json not found!")
        return

    print("📊 ANALYZING MERGED PRs...")
    merged_data = load_json_data(merged_file)

    user_closed_count = 0
    total_with_close_actor = 0
    total_prs = 0
    close_actor_counter = Counter()
    user_closures_by_date = defaultdict(list)

    target_usernames = (
        [github_username, gitlab_username]
        if github_username and gitlab_username
        else [github_username or gitlab_username]
    )

    for repo_name, prs in merged_data.get("data", {}).items():
        for pr in prs:
            total_prs += 1
            close_actor = pr.get("close_actor")

            if close_actor:
                total_with_close_actor += 1
                close_actor_counter[close_actor] += 1

                if close_actor in target_usernames:
                    user_closed_count += 1
                    closed_at = pr.get("closed_at", "")
                    pr_number = pr.get("number", "unknown")
                    pr_title = (
                        pr.get("title", "No title")[:50] + "..."
                        if len(pr.get("title", "")) > 50
                        else pr.get("title", "No title")
                    )

                    user_closures_by_date[
                        closed_at[:10] if closed_at else "no-date"
                    ].append(
                        {
                            "repo": repo_name,
                            "number": pr_number,
                            "title": pr_title,
                            "closed_at": closed_at,
                        }
                    )

    print(f"   Total PRs: {total_prs}")
    print(f"   PRs with close_actor: {total_with_close_actor}")
    print(f"   PRs closed by you: {user_closed_count}")
    print()

    if user_closed_count > 0:
        print(f"🎉 FOUND {user_closed_count} PRs CLOSED BY YOU:")
        for date, prs in sorted(user_closures_by_date.items()):
            print(f"   📅 {date}:")
            for pr in prs:
                print(f"      • {pr['repo']}#{pr['number']}: {pr['title']}")
        print()
    else:
        print("❌ NO PRs FOUND CLOSED BY YOU")
        print()

    print("🔝 TOP 10 CLOSE ACTORS:")
    for actor, count in close_actor_counter.most_common(10):
        marker = "👤 YOU!" if actor in target_usernames else ""
        print(f"   {actor}: {count} PRs {marker}")
    print()

    # Check closed PRs too
    print("📊 ANALYZING CLOSED PRs...")
    closed_data = load_json_data(closed_file)

    user_closed_closed_count = 0
    total_closed_with_close_actor = 0
    total_closed_prs = 0

    for repo_name, prs in closed_data.get("data", {}).items():
        for pr in prs:
            total_closed_prs += 1
            close_actor = pr.get("close_actor")

            if close_actor:
                total_closed_with_close_actor += 1

                if close_actor in target_usernames:
                    user_closed_closed_count += 1

    print(f"   Total closed PRs: {total_closed_prs}")
    print(f"   Closed PRs with close_actor: {total_closed_with_close_actor}")
    print(f"   Closed PRs closed by you: {user_closed_closed_count}")
    print()

    print("📈 SUMMARY:")
    print(f"   Merged PRs you closed: {user_closed_count}")
    print(f"   Closed PRs you closed: {user_closed_closed_count}")
    print(f"   Total PRs you closed: {user_closed_count + user_closed_closed_count}")
    print()

    if user_closed_count == 0:
        print("🤔 POSSIBLE ISSUES:")
        print("   1. Date range filter might be excluding your closures")
        print("   2. Username mismatch in close_actor data")
        print("   3. Missing close_actor data for your PRs")
        print("   4. PRs might be attributed to a different username variation")
        print()
        print("💡 SUGGESTIONS:")
        print("   1. Try removing date filters (use full date range)")
        print("   2. Check if your GitHub display name differs from username")
        print("   3. Look for username variations in the top closers list above")


if __name__ == "__main__":
    debug_close_actor_data()
