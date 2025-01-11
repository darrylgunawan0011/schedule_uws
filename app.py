from flask import Flask, render_template, request, redirect, send_file, make_response
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from openpyxl import load_workbook
from datetime import datetime, timedelta
import pandas as pd
import io
import json
import os

app = Flask(__name__)

SCHEDULE_FILE = "schedule_data.json"
schedule_data = {}
start_date = None

def load_schedule_data():
    """Load schedule data from JSON file."""
    if os.path.exists(SCHEDULE_FILE):
        try:
            with open(SCHEDULE_FILE, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    return {}

def save_schedule_data(data):
    """Save schedule data to JSON file."""
    with open(SCHEDULE_FILE, 'w') as file:
        json.dump(data, file, indent=4)

def generate_empty_schedule():
    """Generate an empty schedule structure."""
    return {
        "Name": [
            "Selix", "Matt", "Christ", "Brian", "Selvi", "Kevin", "Damaris", 
            "Eric", "Moreno", "Karel", "Guaman", "Will", "Era"
        ],
        "Wednesday": [""] * 13,
        "Thursday": [""] * 13,
        "Friday": [""] * 13,
        "Saturday": [""] * 13,
        "Sunday": [""] * 13,
        "Monday": [""] * 13,
        "Tuesday": [""] * 13
    }
    
@app.route('/', methods=['GET', 'POST'])
def index():
    global start_date, schedule_data

    if request.method == 'POST' or request.args.get('start_date'):
        user_date = request.args.get('start_date') or request.form.get('start_date')
        user_date_obj = datetime.strptime(user_date, "%Y-%m-%d")

        # Check if the selected date is a Wednesday
        if user_date_obj.weekday() != 2:  # 2 is Wednesday
            return render_template(
                'index.html',
                error_message="Please select a Wednesday as the starting date for the schedule."
            )

        start_date = user_date
    else:
        # Default to the next Wednesday if no date is provided
        today = datetime.today()
        days_to_next_wednesday = (3 - today.weekday() + 7) % 7  # 3 is Wednesday
        if days_to_next_wednesday == 0:
            days_to_next_wednesday = 7
        next_wednesday = today + timedelta(days=days_to_next_wednesday)
        start_date = next_wednesday.strftime("%Y-%m-%d")

    # Load the schedule data from the JSON file
    all_schedules = load_schedule_data()

    # Check if the selected period exists in the JSON data
    if start_date not in all_schedules:
        print(f"Start date '{start_date}' not found. Creating new schedule.")
        all_schedules[start_date] = {"schedule_data": generate_empty_schedule()}
        save_schedule_data(all_schedules)  # Save the new schedule
    else:
        print(f"Start date '{start_date}' found. Loading schedule.")

    schedule_data = all_schedules[start_date]["schedule_data"]

    # Calculate the dates for the selected period
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    dates = [start_date_obj + timedelta(days=i) for i in range(7)]
    week_dates = {
        'wednesday': dates[0],
        'thursday': dates[1],
        'friday': dates[2],
        'saturday': dates[3],
        'sunday': dates[4],
        'monday': dates[5],
        'tuesday': dates[6]
    }

    period_display = f"Selected Period: {week_dates['wednesday'].strftime('%B %d, %Y')} to {week_dates['tuesday'].strftime('%B %d, %Y')}"
    schedule_list = zip(
        schedule_data["Name"],
        schedule_data["Wednesday"],
        schedule_data["Thursday"],
        schedule_data["Friday"],
        schedule_data["Saturday"],
        schedule_data["Sunday"],
        schedule_data["Monday"],
        schedule_data["Tuesday"]
    )

    return render_template('index.html',
                           schedule_list=schedule_list,
                           wednesday_date=week_dates['wednesday'].strftime('%m/%d'),
                           thursday_date=week_dates['thursday'].strftime('%m/%d'),
                           friday_date=week_dates['friday'].strftime('%m/%d'),
                           saturday_date=week_dates['saturday'].strftime('%m/%d'),
                           sunday_date=week_dates['sunday'].strftime('%m/%d'),
                           monday_date=week_dates['monday'].strftime('%m/%d'),
                           tuesday_date=week_dates['tuesday'].strftime('%m/%d'),
                           period_display=period_display,
                           start_date=start_date,
                           error_message=None)

@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    global schedule_data, start_date

    for day in ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Monday", "Tuesday"]:
        for idx, name in enumerate(schedule_data["Name"]):
            lunch_checkbox = request.form.get(f"Lunch_{day}_{name}")
            other_shift = request.form.get(f"Other_Shifts_{day}_{name}", "N/A")

            if lunch_checkbox:
                schedule_data[day][idx] = f"Lunch {other_shift}" if other_shift != "N/A" else "Lunch"
            else:
                schedule_data[day][idx] = other_shift if other_shift != "N/A" else ""

    all_schedules = load_schedule_data()
    all_schedules[start_date] = {"schedule_data": schedule_data}
    save_schedule_data(all_schedules)

    return redirect(f'/?start_date={start_date}')

@app.route('/clear_schedule', methods=['POST'])
def clear_schedule():
    global schedule_data, start_date

    for day in ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Monday", "Tuesday"]:
        schedule_data[day] = [""] * len(schedule_data["Name"])

    all_schedules = load_schedule_data()
    all_schedules[start_date] = {"schedule_data": schedule_data}
    save_schedule_data(all_schedules)

    return redirect(f'/?start_date={start_date}')

@app.route('/download_excel', methods=['GET'])
def download_excel():
    df = pd.DataFrame(schedule_data)
    excel_file = "worker_schedule.xlsx"
    df.to_excel(excel_file, index=False)
    return send_file(excel_file, as_attachment=True, download_name="worker_schedule.xlsx")

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    global schedule_data, start_date
    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
    week_dates = [start_date_obj + timedelta(days=i) for i in range(7)]

    # Prepare data for the PDF, adding the correct dates
    data = []
    header = ["Name", 
              f"Wed ({week_dates[0].strftime('%m/%d')})", 
              f"Thu ({week_dates[1].strftime('%m/%d')})", 
              f"Fri ({week_dates[2].strftime('%m/%d')})", 
              f"Sat ({week_dates[3].strftime('%m/%d')})", 
              f"Sun ({week_dates[4].strftime('%m/%d')})", 
              f"Mon ({week_dates[5].strftime('%m/%d')})", 
              f"Tue ({week_dates[6].strftime('%m/%d')})"]
    data.append(header)

    # Populate rows with names and corresponding data
    for idx, name in enumerate(schedule_data['Name']):
        row = [name]
        for day in ["Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Monday", "Tuesday"]:
            shift = schedule_data[day][idx]  # Get the corresponding day's shift
            row.append(shift if shift != "N/A" else "")
        data.append(row)

    # Create a PDF in memory with landscape orientation
    buffer = io.BytesIO()
    
    # Set the margins: 1 inch on the left and right
    left_margin = 36  # 1 inch = 72 points
    right_margin = 36  # 1 inch = 72 points
    top_margin = 72
    bottom_margin = 72
    
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                            leftMargin=left_margin, rightMargin=right_margin, 
                            topMargin=top_margin, bottomMargin=bottom_margin)

    # Adjust table width (taking into account the 1-inch left and right margins)
    table_width = doc.pagesize[0] - left_margin - right_margin  # Subtract left and right margins
    col_widths = [table_width * 0.10]  # Name column (15% of table width)
    col_widths += [table_width * 0.12] * 7  # Day columns (12% of table width each)

    # Create the table with the data
    table = Table(data, colWidths=col_widths)

    # Define table style (add borders, increase padding, and adjust font size)
    style = TableStyle([ 
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header background color
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Align all cells center
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Bold header
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # Set a bigger font size for better readability
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # Add grid (borders) around the table
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),  # Line under header
        ('TOPPADDING', (0, 0), (-1, -1), 10),  # Increased top padding for rows
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),  # Increased bottom padding for rows
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])

    table.setStyle(style)

    # Build the PDF
    doc.build([table])

    # Return the PDF as a response
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=schedule.pdf'

    return response

if __name__ == "__main__":
    load_schedule()
    app.run(host='0.0.0.0', port=8181)
