from flask import request, jsonify
from .app import app, logger, client
from .helpers import build_new_ticket_modal
from .config import Config

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

        from .app import sheet
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

# Add other routes here as needed (system-tickets, ticket-summary, slack/events)