from .app import sheet, logger, client
from .config import Config

def is_system_user(user_id):
    logger.debug(f"Checking if user {user_id} is a system user")
    return user_id in Config.SYSTEM_USERS

def find_ticket_by_id(ticket_id):
    logger.debug(f"Finding ticket by ID: {ticket_id}")
    tickets = sheet.get_all_values()
    for i, row in enumerate(tickets):
        if i == 0:  # Skip header row
            continue
        if row[0] == ticket_id:
            logger.debug(f"Ticket {ticket_id} found at row {i}")
            return i, row
    logger.debug(f"Ticket {ticket_id} not found")
    return None, None

def update_ticket_status(ticket_id, status, assigned_to=None, message_ts=None, comment=None, action_user_id=None):
    logger.info(f"Updating ticket status: Ticket ID: {ticket_id}, Status: {status}, Assigned To: {assigned_to}, Comment: {comment}, Action User ID: {action_user_id}")
    try:
        row_index, ticket = find_ticket_by_id(ticket_id)
        if not ticket:
            logger.error("Ticket not found")
            return False

        ticket[5] = status
        if assigned_to:
            ticket[1] = assigned_to
        if comment:
            current_comments = ticket[12] if len(ticket) > 12 else ""
            ticket[12] = f"{current_comments}\n{action_user_id}: {comment}" if current_comments else f"{action_user_id}: {comment}"

        logger.debug(f"Updating row {row_index + 1} in Google Sheet")
        sheet.update(f"A{row_index + 1}:M{row_index + 1}", [ticket])
        logger.info("Row updated successfully")

        if message_ts:
            logger.debug(f"Updating Slack message with timestamp {message_ts}")
            message_blocks = [
                {"type": "header", "text": {"type": "plain_text", "text": "🎫 Ticket Details", "emoji": True}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Ticket ID:* {ticket[0]}\n\n"}},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"📂 *Campaign:* {ticket[2]}\n\n"
                                f"📌 *Issue:* {ticket[3]}\n\n"
                                f"⚡ *Priority:* {ticket[4]} {'🔴' if ticket[4] == 'High' else '🟡' if ticket[4] == 'Medium' else '🔵'}\n\n"
                                f"👤 *Assigned To:* {ticket[1] if ticket[1] != 'Unassigned' else '❌ Unassigned'}\n\n"
                                f"🔄 *Status:* {ticket[5]} {'🟢' if ticket[5] == 'Open' else '🔵' if ticket[5] == 'In Progress' else '🟡' if ticket[5] == 'Resolved' else '🔴'}\n\n"
                    }
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"🖋️ *Details:* {ticket[6]}\n\n"
                                f"🔗 *Salesforce Link:* {ticket[7] or 'N/A'}\n\n"
                    }
                },
                {"type": "section", "text": {"type": "mrkdwn", "text": f"📂 *File Attachment:* {ticket[8]}\n\n"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"📅 *Created Date:* {ticket[10]}\n\n"}},
                {"type": "section", "text": {"type": "mrkdwn", "text": f"💬 *Comments:* {ticket[12] if len(ticket) > 12 and ticket[12] else 'N/A'}\n\n"}},
                {"type": "divider"},
                {
                    "type": "actions",
                    "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "🖐 Assign to Me"}, "action_id": f"assign_to_me_{ticket_id}", "value": ticket_id, "style": "primary"} if is_system_user(action_user_id) and ticket[5] == "Open" and ticket[1] == "Unassigned" else None,
                        {"type": "button", "text": {"type": "plain_text", "text": "🔁 Reassign"}, "action_id": f"reassign_{ticket_id}", "value": ticket_id, "style": "primary"} if is_system_user(action_user_id) and ticket[5] in ["Open", "In Progress"] else None,
                        {"type": "button", "text": {"type": "plain_text", "text": "❌ Close"}, "action_id": f"close_{ticket_id}", "value": ticket_id, "style": "danger"} if is_system_user(action_user_id) and ticket[5] in ["Open", "In Progress"] else None,
                        {"type": "button", "text": {"type": "plain_text", "text": "🟢 Resolve"}, "action_id": f"resolve_{ticket_id}", "value": ticket_id, "style": "primary"} if is_system_user(action_user_id) and ticket[5] in ["Open", "In Progress"] else None,
                        {"type": "button", "text": {"type": "plain_text", "text": "🔄 Reopen"}, "action_id": f"reopen_{ticket_id}", "value": ticket_id} if is_system_user(action_user_id) and ticket[5] in ["Closed", "Resolved"] else None
                    ]
                }
            ]
            message_blocks[-1]["elements"] = [elem for elem in message_blocks[-1]["elements"] if elem is not None]
            client.chat_update(channel=Config.SLACK_CHANNEL, ts=message_ts, blocks=message_blocks)
            logger.info("Slack message updated successfully")

        return True
    except Exception as e:
        logger.error(f"Error updating ticket status: {e}")
        return False

def generate_ticket_id():
    logger.debug("Generating ticket ID")
    tickets = sheet.get_all_values()
    if len(tickets) <= 1:
        return "T1001"
    last_ticket_id = tickets[-1][0]
    if not last_ticket_id.startswith("T"):
        return "T1001"
    number = int(last_ticket_id[1:]) + 1
    return f"T{number}"

def send_direct_message(user_id, message):
    logger.debug(f"Sending direct message to user {user_id}: {message}")
    try:
        client.chat_postMessage(channel=user_id, text=message)
        logger.info("Direct message sent successfully")
    except Exception as e:
        logger.error(f"Error sending directла message: {e}")

def build_new_ticket_modal():
    campaign_options = [
        {"text": {"type": "plain_text", "text": "Camp Lejeune"}, "value": "Camp Lejeune"},
        {"text": {"type": "plain_text", "text": "Maui Wildfires"}, "value": "Maui Wildfires"},
        {"text": {"type": "plain_text", "text": "LA Wildfire"}, "value": "LA Wildfire"},
        {"text": {"type": "plain_text", "text": "Depo-Provera"}, "value": "Depo-Provera"},
        {"text": {"type": "plain_text", "text": "CPP Sick and Family Leave"}, "value": "CPP Sick and Family Leave"}
    ]
    issue_type_options = [
        {"text": {"type": "plain_text", "text": "🖥️ System & Software - Salesforce Performance Issues (Freezing or Crashing)"}, "value": "Salesforce Performance Issues"},
        {"text": {"type": "plain_text", "text": "🖥️ System & Software - Vonage Dialer Functionality Issues"}, "value": "Vonage Dialer Functionality Issues"},
        {"text": {"type": "plain_text", "text": "🖥️ System & Software - Broken or Unresponsive Links (ARA, Co-Counsel, Claim Stage, File Upload, etc.)"}, "value": "Broken or Unresponsive Links"},
        {"text": {"type": "plain_text", "text": "💻 Equipment & Hardware - Laptop Fails to Power On"}, "value": "Laptop Fails to Power On"},
        {"text": {"type": "plain_text", "text": "💻 Equipment & Hardware - Slow Performance or Freezing Laptop"}, "value": "Slow Performance or Freezing Laptop"},
        {"text": {"type": "plain_text", "text": "💻 Equipment & Hardware - Unresponsive Keyboard or Mouse"}, "value": "Unresponsive Keyboard or Mouse"},
        {"text": {"type": "plain_text", "text": "💻 Equipment & Hardware - Headset/Mic Malfunction (No Sound, Static, etc.)"}, "value": "Headset/Microphone Malfunction"},
        {"text": {"type": "plain_text", "text": "💻 Equipment & Hardware - Charger or Battery Failure"}, "value": "Charger or Battery Failure"},
        {"text": {"type": "plain_text", "text": "🔐 Security & Account - Multi-Factor Authentication (MFA) Failure (Security Key)"}, "value": "MFA Failure"},
        {"text": {"type": "plain_text", "text": "🔐 Security & Account - Account Lockout (Gmail or Salesforce)"}, "value": "Account Lockout"},
        {"text": {"type": "plain_text", "text": "📑 Client & Document - Paper Packet Contains Errors or Missing Information"}, "value": "Paper Packet Errors"},
        {"text": {"type": "plain_text", "text": "📑 Client & Document - Paper Packet Mailing Status"}, "value": "Paper Packet Mailing Status"},
        {"text": {"type": "plain_text", "text": "📑 Client & Document - Client Information Update Request"}, "value": "Client Information Update Request"},
        {"text": {"type": "plain_text", "text": "📑 Client & Document - Client System Error (Missing Document Request, Form Submission Failure, Broken or Unresponsive Link)"}, "value": "Client System Error"},
        {"text": {"type": "plain_text", "text": "📊 Management Systems - Reports or Dashboards Failing to Load"}, "value": "Reports or Dashboards Failing to Load"},
        {"text": {"type": "plain_text", "text": "📊 Management Systems - Automated Voicemail System Malfunction"}, "value": "Automated Voicemail System Malfunction"},
        {"text": {"type": "plain_text", "text": "📊 Management Systems - Missing or Inaccessible Call Recordings"}, "value": "Missing or Inaccessible Call Recordings"},
        {"text": {"type": "plain_text", "text": "❓ Other (Not Listed Above)"}, "value": "Other"}
    ]
    priority_options = [
        {"text": {"type": "plain_text", "text": "🔵 Low"}, "value": "Low"},
        {"text": {"type": "plain_text", "text": "🟡 Medium"}, "value": "Medium"},
        {"text": {"type": "plain_text", "text": "🔴 High"}, "value": "High"}
    ]
    return {
        "type": "modal",
        "callback_id": "new_ticket",
        "title": {"type": "plain_text", "text": "Submit a New Ticket"},
        "submit": {"type": "plain_text", "text": "Submit"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "campaign_block",
                "label": {"type": "plain_text", "text": "📂 Campaign"},
                "element": {
                    "type": "static_select",
                    "action_id": "campaign_select",
                    "placeholder": {"type": "plain_text", "text": "Select a campaign"},
                    "options": campaign_options
                },
                "optional": False
            },
            {
                "type": "input",
                "block_id": "issue_type_block",
                "label": {"type": "plain_text", "text": "📌 Issue Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "issue_type_select",
                    "placeholder": {"type": "plain_text", "text": "Select an issue type"},
                    "options": issue_type_options
                },
                "optional": False
            },
            {
                "type": "input",
                "block_id": "priority_block",
                "label": {"type": "plain_text", "text": "⚡ Priority"},
                "element": {
                    "type": "static_select",
                    "action_id": "priority_select",
                    "placeholder": {"type": "plain_text", "text": "Select priority"},
                    "options": priority_options
                },
                "optional": False
            },
            {
                "type": "input",
                "block_id": "details_block",
                "label": {"type": "plain_text", "text": "🗂 Details"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "details_input",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Describe the issue in detail"}
                },
                "optional": False
            },
            {
                "type": "input",
                "block_id": "salesforce_link_block",
                "label": {"type": "plain_text", "text": "📎 Salesforce Link (Optional)"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "salesforce_link_input",
                    "placeholder": {"type": "plain_text", "text": "Paste Salesforce URL"}
                },
                "optional": True
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "📂 *File Upload:* (Optional) Upload the file to Slack and include the file URL in the details field."}
            }
        ]
    }