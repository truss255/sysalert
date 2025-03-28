from flask import request, jsonify
import logging
from apps import app, client
from apps.helpers import build_new_ticket_modal, update_ticket_status, send_direct_message

logger = logging.getLogger(__name__)

# Existing routes
@app.route("/new-ticket", methods=["POST"])
def new_ticket():
    logger.info("Received /new-ticket request")
    try:
        data = request.form
        logger.debug(f"Request form data: {data}")
        trigger_id = data.get("trigger_id")
        logger.debug(f"Trigger ID: {trigger_id}")

        modal = build_new_ticket_modal()
        response = client.views_open(trigger_id=trigger_id, view=modal)
        logger.info(f"New ticket modal opened: {response}")
        return "", 200
    except Exception as e:
        logger.error(f"Error in /new-ticket: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/agent-tickets", methods=["POST"])
def agent_tickets():
    logger.info("Received /agent-tickets request")
    try:
        data = request.form
        logger.debug(f"Request form data: {data}")
        trigger_id = data.get("trigger_id")
        user_id = data.get("user_id")
        logger.debug(f"Trigger ID: {trigger_id}, User ID: {user_id}")

        from config import sheet
        tickets = sheet.get_all_values()[1:]
        logger.debug(f"Total tickets fetched: {len(tickets)}")
        agent_tickets = [row for row in tickets if row[10] == user_id]
        logger.debug(f"Found {len(agent_tickets)} tickets for user {user_id}")

        blocks = [
            {"type": "header", "text": {"type": "plain_text", "text": "🔍 Your Submitted Tickets", "emoji": True}},
            {
                "type": "input",
                "block_id": "status_filter_block",
                "label": {"type": "plain_text", "text": "Filter by Status", "emoji": True},
                "element": {
                    "type": "static_select",
                    "action_id": "status_filter_select",
                    "placeholder": {"type": "plain_text", "text": "Choose a status", "emoji": True},
                    "options": [
                        {"text": {"type": "plain_text", "text": "All"}, "value": "all"},
                        {"text": {"type": "plain_text", "text": "Open"}, "value": "Open"},
                        {"text": {"type": "plain_text", "text": "In Progress"}, "value": "In Progress"},
                        {"text": {"type": "plain_text", "text": "Resolved"}, "value": "Resolved"},
                        {"text": {"type": "plain_text", "text": "Closed"}, "value": "Closed"}
                    ],
                    "initial_option": {"text": {"type": "plain_text", "text": "All"}, "value": "all"}
                }
            },
            {"type": "divider"}
        ]

        if not agent_tickets:
            logger.debug("No tickets found for this user")
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "🎉 You have no submitted tickets.\n\n"}})
        else:
            logger.debug("Adding tickets to modal blocks")
            for ticket in agent_tickets:
                ticket_id = ticket[0]
                status = ticket[5]
                campaign = ticket[2]
                issue = ticket[3]
                created_date = ticket[10]
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{ticket_id}* _({status} {'🟢' if status == 'Open' else '🔵' if status == 'In Progress' else '🟡' if status == 'Resolved' else '🔴'})_\n\n"
                                f"*Campaign:* {campaign}\n\n"
                                f"*Issue:* {issue}\n\n"
                                f"*Date:* {created_date}\n\n"
                    }
                })
                blocks.append({"type": "divider"})

        modal = {
            "type": "modal",
            "callback_id": "agent_tickets_view",
            "title": {"type": "plain_text", "text": "Your Tickets", "emoji": True},
            "close": {"type": "plain_text", "text": "Close", "emoji": True},
            "blocks": blocks
        }

        response = client.views_open(trigger_id=trigger_id, view=modal)
        logger.info(f"Agent tickets modal opened: {response}")
        return "", 200
    except Exception as e:
        logger.error(f"Error in /agent-tickets: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# New route for Slack events and interactivity
@app.route("/slack/events", methods=["POST"])
def slack_events():
    logger.info("Received request at /slack/events")
    try:
        # Handle URL verification challenge (Slack sends this to verify the endpoint)
        if "challenge" in request.json:
            logger.debug("Received URL verification challenge")
            return jsonify({"challenge": request.json["challenge"]})

        # Handle events and interactivity payloads
        payload = request.json
        logger.debug(f"Received payload: {payload}")

        # Handle view submissions (e.g., when a user submits the new ticket modal)
        if payload.get("type") == "view_submission":
            callback_id = payload["view"]["callback_id"]
            if callback_id == "new_ticket":
                # Extract values from the modal submission
                values = payload["view"]["state"]["values"]
                campaign = values["campaign_block"]["campaign_select"]["selected_option"]["value"]
                issue_type = values["issue_type_block"]["issue_type_select"]["selected_option"]["value"]
                priority = values["priority_block"]["priority_select"]["selected_option"]["value"]
                details = values["details_block"]["details_input"]["value"]
                salesforce_link = values.get("salesforce_link_block", {}).get("salesforce_link_input", {}).get("value", "N/A")
                user_id = payload["user"]["id"]

                # Generate a ticket ID
                from helpers import generate_ticket_id
                ticket_id = generate_ticket_id()

                # Log the ticket to Google Sheets
                from config import sheet
                from datetime import datetime
                created_date = datetime.now().strftime("%m/%d/%Y")
                ticket_data = [
                    ticket_id, "Unassigned", campaign, issue_type, priority, "Open",
                    details, salesforce_link, "N/A", created_date, user_id, created_date, ""
                ]
                sheet.append_row(ticket_data)
                logger.info(f"Ticket {ticket_id} logged to Google Sheets")

                # Post the ticket to Slack
                message_blocks = [
                    {"type": "header", "text": {"type": "plain_text", "text": "🎫 Ticket Details", "emoji": True}},
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"✅ *Ticket ID:* {ticket_id}\n\n"}},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"📂 *Campaign:* {campaign}\n\n"
                                    f"📌 *Issue:* {issue_type}\n\n"
                                    f"⚡ *Priority:* {priority} {'🔴' if priority == 'High' else '🟡' if priority == 'Medium' else '🔵'}\n\n"
                                    f"👤 *Assigned To:* Unassigned\n\n"
                                    f"🔄 *Status:* Open 🟢\n\n"
                        }
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"🖋️ *Details:* {details}\n\n"
                                    f"🔗 *Salesforce Link:* {salesforce_link}\n\n"
                        }
                    },
                    {"type": "section", "text": {"type": "mrkdwn", "text": f"📅 *Created Date:* {created_date}\n\n"}},
                    {"type": "divider"},
                    {
                        "type": "actions",
                        "elements": [
                            {"type": "button", "text": {"type": "plain_text", "text": "🖐 Assign to Me"}, "action_id": f"assign_to_me_{ticket_id}", "value": ticket_id, "style": "primary"},
                            {"type": "button", "text": {"type": "plain_text", "text": "❌ Close"}, "action_id": f"close_{ticket_id}", "value": ticket_id, "style": "danger"},
                            {"type": "button", "text": {"type": "plain_text", "text": "🟢 Resolve"}, "action_id": f"resolve_{ticket_id}", "value": ticket_id, "style": "primary"}
                        ]
                    }
                ]
                response = client.chat_postMessage(channel="#systems-issues", blocks=message_blocks)
                logger.info(f"Ticket {ticket_id} posted to Slack")

                # Send a confirmation to the user
                send_direct_message(user_id, f"✅ Your ticket ({ticket_id}) has been submitted successfully!")
                return "", 200

        # Handle button clicks (e.g., "Assign to Me", "Close", "Resolve")
        if payload.get("type") == "block_actions":
            action = payload["actions"][0]
            action_id = action["action_id"]
            ticket_id = action["value"]
            user_id = payload["user"]["id"]

            if action_id.startswith("assign_to_me_"):
                update_ticket_status(ticket_id, "In Progress", assigned_to=user_id, message_ts=payload["message"]["ts"], action_user_id=user_id)
                send_direct_message(user_id, f"✅ You have been assigned to ticket {ticket_id}.")
            elif action_id.startswith("close_"):
                update_ticket_status(ticket_id, "Closed", message_ts=payload["message"]["ts"], action_user_id=user_id)
                send_direct_message(user_id, f"✅ Ticket {ticket_id} has been closed.")
            elif action_id.startswith("resolve_"):
                update_ticket_status(ticket_id, "Resolved", message_ts=payload["message"]["ts"], action_user_id=user_id)
                send_direct_message(user_id, f"✅ Ticket {ticket_id} has been resolved.")

            return "", 200

        return "", 200
    except Exception as e:
        logger.error(f"Error in /slack/events: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500