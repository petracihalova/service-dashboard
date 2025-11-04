"""Google Drive and Google Docs integration service using OAuth 2.0."""

import logging
import os
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config

logger = logging.getLogger(__name__)


class GoogleDriveService:
    """Service for interacting with Google Drive and Google Docs APIs."""

    # Scopes for accessing Google Drive and creating documents
    SCOPES = [
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/documents",
    ]

    def __init__(self):
        """Initialize Google Drive service with credentials."""
        self.credentials = None
        self.drive_service = None
        self.docs_service = None
        self._initialize_services()

    def _initialize_services(self):
        """Initialize Google Drive and Docs services with OAuth credentials."""
        try:
            oauth_creds_path = os.path.join(
                config.DATA_PATH_FOLDER, "oauth_credentials.json"
            )
            token_path = os.path.join(config.DATA_PATH_FOLDER, "token.json")

            if not os.path.exists(oauth_creds_path):
                logger.warning(
                    "OAuth credentials not found. "
                    "Run 'python authorize_google.py' to set up Google Drive integration. "
                    "See OAUTH_SETUP.md for details."
                )
                return

            logger.info("Found OAuth credentials, attempting authentication")
            self.credentials = self._get_oauth_credentials(oauth_creds_path, token_path)

            if self.credentials:
                # Build services with OAuth
                self.drive_service = build("drive", "v3", credentials=self.credentials)
                self.docs_service = build("docs", "v1", credentials=self.credentials)
                logger.info("Google Drive and Docs services initialized successfully")
            else:
                logger.warning(
                    "Failed to get OAuth credentials. "
                    "Run 'python authorize_google.py' to authorize the application."
                )

        except Exception as e:
            logger.error(f"Failed to initialize Google services: {e}")
            self.drive_service = None
            self.docs_service = None

    def _get_oauth_credentials(self, creds_path, token_path):
        """Get OAuth credentials, refreshing if needed."""
        creds = None

        # Load existing token if available
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, self.SCOPES)
                logger.info("Loaded existing OAuth token")
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")

        # Refresh or get new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed OAuth token")
                except Exception as e:
                    logger.warning(f"Failed to refresh token: {e}")
                    creds = None

            if not creds:
                logger.info(
                    "OAuth token not found or invalid. Run 'python authorize_google.py' to authorize."
                )
                return None

            # Save the credentials for the next run
            try:
                with open(token_path, "w") as token:
                    token.write(creds.to_json())
                logger.info("Saved OAuth token")
            except Exception as e:
                logger.warning(f"Failed to save token: {e}")

        return creds

    def is_available(self) -> bool:
        """Check if Google Drive service is available."""
        return self.drive_service is not None and self.docs_service is not None

    def create_release_notes_doc(
        self,
        deployment_name: str,
        release_notes: dict,
        folder_id: str,
    ) -> dict:
        """
        Create a Google Doc with release notes in the specified folder.

        Args:
            deployment_name: Name of the deployment
            release_notes: Dictionary containing release notes data
            folder_id: Google Drive folder ID (required)

        Returns:
            dict: Contains success status, document ID, and document URL

        Raises:
            Exception: If document creation fails
        """
        if not self.is_available():
            raise Exception(
                "Google Drive service is not available. Please run 'python authorize_google.py' to set up OAuth."
            )

        if not folder_id:
            raise Exception(
                "No folder ID provided. Folder must be specified for document creation."
            )

        try:
            target_folder_id = folder_id

            # Create document title with date
            today = datetime.now().strftime("%Y-%m-%d")
            doc_title = f"{today} {deployment_name.title()} Release Notes"

            # Create the document
            logger.info(f"Creating Google Doc: {doc_title}")
            doc = (
                self.docs_service.documents()
                .create(body={"title": doc_title})
                .execute()
            )
            doc_id = doc.get("documentId")
            logger.info(f"Document created with ID: {doc_id}")

            # Move document to folder if folder_id is provided
            if target_folder_id:
                try:
                    file = (
                        self.drive_service.files()
                        .get(fileId=doc_id, fields="parents", supportsAllDrives=True)
                        .execute()
                    )
                    previous_parents = ",".join(file.get("parents", []))

                    # Move the file to the new folder
                    file = (
                        self.drive_service.files()
                        .update(
                            fileId=doc_id,
                            addParents=target_folder_id,
                            removeParents=previous_parents,
                            fields="id, parents",
                            supportsAllDrives=True,
                        )
                        .execute()
                    )
                    logger.info(f"Document moved to folder: {target_folder_id}")
                except HttpError as error:
                    logger.warning(
                        f"Failed to move document to folder {target_folder_id}: {error}"
                    )
                    # Continue anyway, document is created just not in the right folder

            # Format and add content to the document
            self._add_release_notes_content(doc_id, release_notes, deployment_name)

            # Get document URL
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"

            logger.info(f"Release notes document created successfully: {doc_url}")

            return {
                "success": True,
                "document_id": doc_id,
                "document_url": doc_url,
                "document_title": doc_title,
            }

        except HttpError as error:
            logger.error(f"Google API error creating document: {error}")
            raise Exception(f"Failed to create Google Doc: {error}")
        except Exception as e:
            logger.error(f"Error creating release notes document: {e}")
            raise Exception(f"Failed to create release notes document: {e}")

    def _format_datetime(self, dt_string: str) -> str:
        """
        Format ISO datetime string to readable format.

        Args:
            dt_string: ISO format datetime string (e.g., "2025-10-22T13:47:20.128Z")

        Returns:
            Formatted string (e.g., "October 22, 2025")
        """
        if not dt_string:
            return ""

        try:
            # Parse ISO format datetime
            if "T" in dt_string:
                # Remove timezone info if present (Z means UTC)
                dt_string_clean = dt_string.replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_string_clean)
            else:
                # Try parsing as date only
                dt = datetime.strptime(dt_string, "%Y-%m-%d")

            return dt.strftime("%B %d, %Y")
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{dt_string}': {e}")
            return dt_string

    def _add_release_notes_content(
        self, doc_id: str, release_notes: dict, deployment_name: str
    ):
        """
        Add formatted content to the release notes document.

        Args:
            doc_id: Google Doc ID
            release_notes: Dictionary containing release notes data
            deployment_name: Name of the deployment
        """
        try:
            repo_name = release_notes.get("repo_name", "").split("/")[-1]
            today = datetime.now().strftime("%B %d, %Y")

            # Build requests for batch update
            requests = []

            # Start building content from the end (Google Docs API inserts at index 1)
            content_parts = []

            # Title
            content_parts.append(
                {
                    "text": f"Release notes {repo_name.replace('-', ' ').upper()}\n",
                    "style": "HEADING_1",
                }
            )

            # Prod release date
            content_parts.append(
                {"text": f"Prod release date: {today}\n\n", "style": "HEADING_2"}
            )

            # Links section
            content_parts.append({"text": "Links:\n", "style": "HEADING_2"})

            links = [
                ("GitHub repo", release_notes.get("repo_link", "")),
                ("Image repo", release_notes.get("image_link", "")),
                ("Deployment config", release_notes.get("app_interface_link", "")),
                (
                    "Release notes Google Disk",
                    release_notes.get("release_notes_link", ""),
                ),
            ]

            for link_text, link_url in links:
                if link_url:
                    content_parts.append(
                        {
                            "text": link_text,
                            "style": "NORMAL_TEXT",
                            "bullet": True,
                            "link": link_url,
                        }
                    )
                    content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})

            content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})

            # Current state
            content_parts.append({"text": "Current state:\n", "style": "HEADING_2"})

            last_prod_mr = release_notes.get("last_release_prod_MR", {})
            if last_prod_mr:
                mr_url = last_prod_mr.get("url", "")
                mr_number = mr_url.split("/")[-1] if mr_url else ""
                merged_at = self._format_datetime(last_prod_mr.get("merged_at", ""))
                content_parts.append(
                    {
                        "text": "Last prod release MR: ",
                        "style": "NORMAL_TEXT",
                        "bullet": True,
                    }
                )
                content_parts.append(
                    {
                        "text": f"MR#{mr_number}",
                        "style": "NORMAL_TEXT",
                        "bold": True,
                        "link": mr_url,
                    }
                )
                content_parts.append(
                    {"text": f" merged on {merged_at}\n", "style": "NORMAL_TEXT"}
                )

            commit_prod = release_notes.get("commit_prod", "")[:7]
            commit_stage = release_notes.get("commit_stage", "")[:7]
            target_commit_short = release_notes.get("target_prod_commit", commit_stage)[
                :7
            ]
            target_commit_full = release_notes.get("target_prod_commit", commit_stage)

            content_parts.append(
                {"text": "PROD commit: ", "style": "NORMAL_TEXT", "bullet": True}
            )
            content_parts.append(
                {
                    "text": commit_prod,
                    "style": "NORMAL_TEXT",
                    "bold": True,
                    "color": {"red": 0.18, "green": 0.49, "blue": 0.196},
                }
            )
            content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})

            content_parts.append(
                {"text": "STAGE commit: ", "style": "NORMAL_TEXT", "bullet": True}
            )
            content_parts.append(
                {
                    "text": commit_stage,
                    "style": "NORMAL_TEXT",
                    "bold": True,
                    "color": {"red": 0.18, "green": 0.49, "blue": 0.196},
                }
            )
            content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})

            repo_link = release_notes.get("repo_link", "")
            if repo_link:
                diff_link = f"{repo_link}/compare/{commit_prod}...{target_commit_short}"
                content_parts.append(
                    {
                        "text": "STAGE / PROD diff: ",
                        "style": "NORMAL_TEXT",
                        "bullet": True,
                    }
                )
                content_parts.append(
                    {"text": "link", "style": "NORMAL_TEXT", "link": diff_link}
                )
                content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})

            content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})

            # New state
            content_parts.append({"text": "New state:\n", "style": "HEADING_2"})
            content_parts.append(
                {"text": "New PROD commit: ", "style": "NORMAL_TEXT", "bullet": True}
            )
            content_parts.append(
                {
                    "text": target_commit_full,
                    "style": "NORMAL_TEXT",
                    "bold": True,
                    "color": {"red": 0.18, "green": 0.49, "blue": 0.196},
                }
            )
            content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})
            content_parts.append(
                {
                    "text": "New PROD release MR:\n\n",
                    "style": "NORMAL_TEXT",
                    "bullet": True,
                }
            )

            # Scope section
            content_parts.append(
                {
                    "text": "Scope:\n",
                    "style": "HEADING_2",
                }
            )
            content_parts.append(
                {
                    "text": "PRs and related Jiras in scope with QE status.\n\n",
                    "style": "NORMAL_TEXT",
                }
            )

            # Pull requests
            prod_stage_pulls = release_notes.get("prod_stage_pulls", [])
            for pr in prod_stage_pulls:
                pr_number = pr.get("number", "")
                pr_title = pr.get("title", "")
                pr_user = pr.get("user_login", "")
                pr_url = pr.get("html_url", "")
                merged_at = self._format_datetime(pr.get("merged_at", ""))

                pr_type = "PR" if "github" in pr_url else "MR"

                # Check if it's a bot PR
                is_bot = "[bot]" in pr_user.lower() or "konflux" in pr_user.lower()

                content_parts.append(
                    {
                        "text": f"{pr_type}#{pr_number}",
                        "style": "NORMAL_TEXT",
                        "bold": True,
                        "link": pr_url,
                        "bullet": True,
                    }
                )

                # Add bot label with yellow background if applicable
                if is_bot:
                    content_parts.append(
                        {
                            "text": " [bot]",
                            "style": "NORMAL_TEXT",
                            "background_color": {"red": 1.0, "green": 1.0, "blue": 0.0},
                        }
                    )

                content_parts.append(
                    {
                        "text": ": ",
                        "style": "NORMAL_TEXT",
                    }
                )
                content_parts.append(
                    {
                        "text": pr_title,
                        "style": "NORMAL_TEXT",
                        "bold": True,
                    }
                )
                content_parts.append(
                    {
                        "text": f" ({pr_user}) {merged_at}\n",
                        "style": "NORMAL_TEXT",
                    }
                )

                # Add JIRA tickets
                jira_tickets = pr.get("jira_tickets", [])
                if jira_tickets:
                    for ticket in jira_tickets:
                        ticket_id = ticket.get("ticket_id", "")
                        ticket_title = ticket.get("title", "")
                        assigned_user = ticket.get("assigned_user", "")
                        ticket_url = f"https://issues.redhat.com/browse/{ticket_id}"

                        content_parts.append(
                            {
                                "text": ticket_id,
                                "style": "NORMAL_TEXT",
                                "bold": True,
                                "link": ticket_url,
                                "bullet": True,
                                "indent": 1,
                            }
                        )
                        content_parts.append(
                            {
                                "text": f": {ticket_title} ({assigned_user})\n",
                                "style": "NORMAL_TEXT",
                            }
                        )

                # Add QE comment
                qe_comment = pr.get("qe_comment")
                if qe_comment:
                    comment_body = qe_comment.get("comment_body", "")
                    comment_author = qe_comment.get("comment_author", "")
                    content_parts.append(
                        {
                            "text": f"QE status: {comment_body} ({comment_author})\n",
                            "style": "NORMAL_TEXT",
                            "bullet": True,
                            "indent": 1,
                        }
                    )
                else:
                    content_parts.append(
                        {
                            "text": "QE status:\n",
                            "style": "NORMAL_TEXT",
                            "bullet": True,
                            "indent": 1,
                        }
                    )

                content_parts.append({"text": "\n", "style": "NORMAL_TEXT"})

            # Insert all text first
            full_text = "".join([part["text"] for part in content_parts])
            document_length = len(full_text) + 1
            requests.append(
                {"insertText": {"location": {"index": 1}, "text": full_text}}
            )

            # Apply styles
            current_index = 1
            heading_ranges = []  # Track heading ranges to make them bold after font is applied
            bold_ranges = []  # Track all bold text ranges to reapply after font is applied

            for part in content_parts:
                text_length = len(part["text"])
                style = part.get("style", "NORMAL_TEXT")

                # Apply heading styles
                if style == "HEADING_1":
                    requests.append(
                        {
                            "updateParagraphStyle": {
                                "range": {
                                    "startIndex": current_index,
                                    "endIndex": current_index + text_length,
                                },
                                "paragraphStyle": {"namedStyleType": "HEADING_1"},
                                "fields": "namedStyleType",
                            }
                        }
                    )
                    # Track this heading to make it bold later (after font is applied)
                    heading_ranges.append(
                        {
                            "startIndex": current_index,
                            "endIndex": current_index + text_length,
                        }
                    )
                elif style == "HEADING_2":
                    requests.append(
                        {
                            "updateParagraphStyle": {
                                "range": {
                                    "startIndex": current_index,
                                    "endIndex": current_index + text_length,
                                },
                                "paragraphStyle": {"namedStyleType": "HEADING_2"},
                                "fields": "namedStyleType",
                            }
                        }
                    )
                    # Track this heading to make it bold later (after font is applied)
                    heading_ranges.append(
                        {
                            "startIndex": current_index,
                            "endIndex": current_index + text_length,
                        }
                    )

                # Track bold formatting (apply after font is set)
                if part.get("bold"):
                    bold_ranges.append(
                        {
                            "startIndex": current_index,
                            "endIndex": current_index + text_length,
                        }
                    )

                # Apply color formatting
                if part.get("color"):
                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": current_index,
                                    "endIndex": current_index + text_length,
                                },
                                "textStyle": {
                                    "foregroundColor": {
                                        "color": {"rgbColor": part["color"]}
                                    }
                                },
                                "fields": "foregroundColor",
                            }
                        }
                    )

                # Apply background color formatting
                if part.get("background_color"):
                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": current_index,
                                    "endIndex": current_index + text_length,
                                },
                                "textStyle": {
                                    "backgroundColor": {
                                        "color": {"rgbColor": part["background_color"]}
                                    }
                                },
                                "fields": "backgroundColor",
                            }
                        }
                    )

                # Apply hyperlink
                if part.get("link"):
                    requests.append(
                        {
                            "updateTextStyle": {
                                "range": {
                                    "startIndex": current_index,
                                    "endIndex": current_index + text_length,
                                },
                                "textStyle": {
                                    "link": {"url": part["link"]},
                                    "foregroundColor": {
                                        "color": {
                                            "rgbColor": {
                                                "blue": 0.8,
                                                "green": 0.33,
                                                "red": 0.06,
                                            }
                                        }
                                    },
                                },
                                "fields": "link,foregroundColor",
                            }
                        }
                    )

                # Track bullet paragraphs (apply after all text styling)
                if part.get("bullet"):
                    # Find the end of this paragraph (next \n)
                    paragraph_start = current_index
                    # Find the end index by looking for newline in the text
                    remaining_text = full_text[current_index:]
                    newline_pos = remaining_text.find("\n")
                    if newline_pos != -1:
                        paragraph_end = current_index + newline_pos + 1
                    else:
                        paragraph_end = current_index + text_length

                    # Create bullet for this paragraph with proper nesting level
                    indent_level = part.get("indent", 0)
                    requests.append(
                        {
                            "createParagraphBullets": {
                                "range": {
                                    "startIndex": paragraph_start,
                                    "endIndex": paragraph_end,
                                },
                                "bulletPreset": "BULLET_DISC_CIRCLE_SQUARE",
                            }
                        }
                    )

                    # Set proper indentation for bullet hierarchy
                    # Level 0: indentFirstLine=18, indentStart=36
                    # Level 1: indentFirstLine=54, indentStart=72
                    # Level N: indentFirstLine=18+(36*N), indentStart=36+(36*N)
                    requests.append(
                        {
                            "updateParagraphStyle": {
                                "range": {
                                    "startIndex": paragraph_start,
                                    "endIndex": paragraph_end,
                                },
                                "paragraphStyle": {
                                    "indentFirstLine": {
                                        "magnitude": 18 + (36 * indent_level),
                                        "unit": "PT",
                                    },
                                    "indentStart": {
                                        "magnitude": 36 + (36 * indent_level),
                                        "unit": "PT",
                                    },
                                },
                                "fields": "indentStart,indentFirstLine",
                            }
                        }
                    )

                current_index += text_length

            # Apply Red Hat Display font to entire document
            logger.info(
                f"Applying Red Hat Display font to document, range: 1 to {document_length}"
            )
            requests.append(
                {
                    "updateTextStyle": {
                        "range": {
                            "startIndex": 1,
                            "endIndex": document_length,
                        },
                        "textStyle": {
                            "weightedFontFamily": {
                                "fontFamily": "Red Hat Display",
                                "weight": 400,
                            }
                        },
                        "fields": "weightedFontFamily",
                    }
                }
            )

            # Make all headings bold (AFTER font is applied so it's not overridden)
            for heading_range in heading_ranges:
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": heading_range,
                            "textStyle": {"bold": True},
                            "fields": "bold",
                        }
                    }
                )

            # Make all other bold text bold (AFTER font is applied so it's not overridden)
            for bold_range in bold_ranges:
                requests.append(
                    {
                        "updateTextStyle": {
                            "range": bold_range,
                            "textStyle": {"bold": True},
                            "fields": "bold",
                        }
                    }
                )

            # Execute batch update
            self.docs_service.documents().batchUpdate(
                documentId=doc_id, body={"requests": requests}
            ).execute()

            logger.info(f"Content added to document {doc_id}")

        except Exception as e:
            logger.error(f"Error adding content to document: {e}")
            # Don't raise here - document is created, just content might be incomplete

    def get_folder_info(self, folder_id: str) -> dict:
        """
        Get information about a Google Drive folder.

        Args:
            folder_id: Google Drive folder ID

        Returns:
            dict: Folder information including name and web link
        """
        if not self.is_available():
            raise Exception("Google Drive service is not available")

        try:
            folder = (
                self.drive_service.files()
                .get(
                    fileId=folder_id,
                    fields="id, name, webViewLink",
                    supportsAllDrives=True,
                )
                .execute()
            )
            return {
                "success": True,
                "folder_id": folder.get("id"),
                "folder_name": folder.get("name"),
                "folder_url": folder.get("webViewLink"),
            }
        except HttpError as error:
            logger.error(f"Error getting folder info: {error}")
            raise Exception(f"Failed to get folder information: {error}")
