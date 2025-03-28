from . import scheduler, logger, client, sheet, weekly_counts_sheet
from .config import Config
from datetime import datetime
import pytz

def generate_weekly_summary():
    """Generate and post a weekly ticket summary to the Slack channel."""
    try:
        logger.info("Generating weekly summary...")
        tickets = sheet.get_all_values()[1:]  # Skip header row
        total_tickets = len(tickets)
        open_tickets = len([row for row in tickets if row[5] == "Open"])
        in_progress_tickets = len([row for row in tickets if row[5] == "In Progress"])
        resolved_tickets = len([row for row in tickets if row[5] == "Resolved"])
        closed_tickets = len([row for row in tickets if row[5] == "Closed"])

        summary = (
            f"📊 *Weekly Ticket Summary*\n\n"
            f"📋 *Total Tickets:* {total_tickets}\n"
            f"🟢 *Open:* {open_tickets}\n"
            f"🔵 *In Progress:* {in_progress_tickets}\n"
            f"🟡 *Resolved:* {resolved_tickets}\n"
            f"🔴 *Closed:* {closed_tickets}\n"
        )

        client.chat_postMessage(channel=Config.SLACK_CHANNEL, text=summary)
        logger.info("Weekly summary posted.")

        # Update WeeklyCounts sheet
        week_number = datetime.now(pytz.timezone(Config.TIMEZONE)).isocalendar()[1]
        new_row = [week_number, total_tickets, open_tickets, in_progress_tickets, resolved_tickets, closed_tickets]
        weekly_counts_sheet.append_row(new_row)
        logger.info("WeeklyCounts sheet updated.")
    except Exception as e:
        logger.error(f"Error in weekly summary: {e}")

def check_overdue_tickets():
    """Check for overdue tickets and notify assignees."""
    try:
        logger.info("Checking for overdue tickets...")
        tickets = sheet.get_all_values()[1:]  # Skip header row
        today = datetime.now(pytz.timezone(Config.TIMEZONE)).date()

        for row in tickets:
            if row[5] in ["Open", "In Progress"]:
                created_date = datetime.strptime(row[10], "%m/%d/%Y").date()
                days_open = (today - created_date).days
                if days_open > 7:  # Overdue after 7 days
                    ticket_id = row[0]
                    assignee_id = row[1]
                    if assignee_id and assignee_id != "Unassigned":
                        client.chat_postMessage(
                            channel=assignee_id,
                            text=f"⏰ Reminder: Ticket {ticket_id} is overdue (open for {days_open} days). Please review."
                        )
                        logger.info(f"Sent overdue reminder for ticket {ticket_id} to {assignee_id}")
    except Exception as e:
        logger.error(f"Error in overdue ticket check: {e}")

def pin_high_priority_unassigned_tickets():
    """Pin high-priority unassigned tickets in the Slack channel."""
    try:
        logger.info("Checking for high-priority unassigned tickets to pin...")
        tickets = sheet.get_all_values()[1:]  # Skip header row
        high_priority_unassigned = [
            row for row in tickets if row[4] == "High" and row[1] == "Unassigned" and row[5] in ["Open", "In Progress"]
        ]

        if high_priority_unassigned:
            ticket_list = "\n".join([f"- *{row[0]}*: {row[3]}" for row in high_priority_unassigned])
            message = f"🚨 *High-Priority Unassigned Tickets*\n\n{ticket_list}\n\nPlease assign these tickets as soon as possible."
            response = client.chat_postMessage(channel=Config.SLACK_CHANNEL, text=message)
            client.pins_add(channel=Config.SLACK_CHANNEL, timestamp=response["ts"])
            logger.info(f"Pinned high-priority unassigned tickets: {len(high_priority_unassigned)} tickets")
        else:
            logger.info("No high-priority unassigned tickets to pin.")
    except Exception as e:
        logger.error(f"Error in pinning high-priority unassigned tickets: {e}")

# Schedule tasks
scheduler.add_job(generate_weekly_summary, "cron", day_of_week="mon", hour=9, minute=0)
scheduler.add_job(check_overdue_tickets, "cron", day_of_week="mon", hour=9, minute=0)
scheduler.add_job(pin_high_priority_unassigned_tickets, "interval", hours=1)
logger.info("Scheduler tasks added.")