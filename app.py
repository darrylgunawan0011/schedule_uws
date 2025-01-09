from openpyxl import load_workbook
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from flask import Flask, render_template, request, redirect, send_file, make_response, session
import os
import pandas as pd
import io
from datetime import datetime, timedelta

app = Flask(__name__)

# Example worker names and shift data
schedule_data = {
    "Name": ["Selix", "Matt", "Christ", "Brian", "Selvi", " ", " ", "Kevin", "Damaris", "Eric", " ", "Moreno", "Karel", "Guaman", " ", " ", "Will", "Era"],
    "Wednesday": [""] * 11,
    "Thursday": [""] * 11,
    "Friday": [""] * 11,
    "Saturday": [""] * 11,
    "Sunday": [""] * 11,
    "Monday": [""] * 11,
    "Tuesday": [""] * 11,
}

start_date = None

@app.route('/', methods=['GET', 'POST'])
def index():
    global start_date

    # Handle setting the start date via the form or URL
    if request.method == 'POST':
        start_date = request.form.get('start_date')  # Get the selected start date from form

    # Calculate the dates for each day of the schedule
    if start_date:
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

        # Display the selected period
        period_display = f"Selected Period: {week_dates['wednesday'].strftime('%B %d, %Y')} to {week_dates['tuesday'].strftime('%B %d, %Y')}"
    else:
        # Default to current week if no start date is set
        week_dates = {
            'wednesday': datetime.now() + timedelta(days=(2 - datetime.now().weekday())),
            'thursday': datetime.now() + timedelta(days=(3 - datetime.now().weekday())),
            'friday': datetime.now() + timedelta(days=(4 - datetime.now().weekday())),
            'saturday': datetime.now() + timedelta(days=(5 - datetime.now().weekday())),
            'sunday': datetime.now() + timedelta(days=(6 - datetime.now().weekday())),
            'monday': datetime.now() + timedelta(days=(7 - datetime.now().weekday())),
            'tuesday': datetime.now() + timedelta(days=(1 - datetime.now().weekday()))
        }

        period_display = "No period selected yet."

    schedule_list = zip(schedule_data['Name'], schedule_data['Wednesday'], schedule_data['Thursday'], schedule_data['Friday'], 
                        schedule_data['Saturday'], schedule_data['Sunday'], schedule_data['Monday'], schedule_data['Tuesday'])

    # Pass the week dates and period display to the template
    return render_template('index.html', schedule_list=schedule_list, 
                           wednesday_date=week_dates['wednesday'].strftime('%m/%d'),
                           thursday_date=week_dates['thursday'].strftime('%m/%d'),
                           friday_date=week_dates['friday'].strftime('%m/%d'),
                           saturday_date=week_dates['saturday'].strftime('%m/%d'),
                           sunday_date=week_dates['sunday'].strftime('%m/%d'),
                           monday_date=week_dates['monday'].strftime('%m/%d'),
                           tuesday_date=week_dates['tuesday'].strftime('%m/%d'),
                           period_display=period_display)

@app.route('/set_schedule_period', methods=['POST', 'GET'])
def set_schedule_period():
    global start_date
    if request.method == 'POST':
        start_date = request.form['start_date']
    else:
        start_date = request.args.get('start_date')

    return redirect('/')

@app.route('/update_schedule', methods=['POST'])
def update_schedule():
    global schedule_data
    for day in ['Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Monday', 'Tuesday']:
        for idx, name in enumerate(schedule_data['Name']):
            # Get the checkbox status for Lunch (if checked, it adds 'Lunch')
            lunch_checkbox = request.form.get(f"Lunch_{day}_{name}")

            # Get the selected other shift for the day (dropdown selection)
            other_shift = request.form.get(f"Other_Shifts_{day}_{name}", "N/A")  # Default to "N/A" if nothing selected

            # If Lunch is checked, we combine Lunch with the dropdown shift (if selected) with a space in between
            if lunch_checkbox:
                if other_shift != "N/A":
                    # If a dropdown value is selected, combine Lunch and that value with a space
                    schedule_data[day][idx] = f"Lunch {other_shift}"
                else:
                    # Only "Lunch" if no dropdown value is selected
                    schedule_data[day][idx] = "Lunch"
            else:
                # If Lunch is not checked, only use the selected dropdown value (or empty if none selected)
                if other_shift != "N/A":
                    schedule_data[day][idx] = other_shift
                else:
                    schedule_data[day][idx] = ""  # Empty if nothing is selected

    return redirect('/')

@app.route('/clear_schedule', methods=['POST'])
def clear_schedule():
    global schedule_data
    for day in schedule_data:
        if day != 'Name':  # Skip the 'Name' column
            schedule_data[day] = [''] * len(schedule_data['Name'])
    return redirect('/')

@app.route('/download_excel', methods=['GET'])
def download_excel():
    # Convert the schedule data into a DataFrame
    df = pd.DataFrame(schedule_data)

    # Save the DataFrame to an Excel file
    excel_file = "worker_schedule.xlsx"
    df.to_excel(excel_file, index=False)

    # Send the Excel file as a downloadable file
    return send_file(excel_file, as_attachment=True, download_name="worker_schedule.xlsx")

def convert_excel_to_pdf(excel_file):
    # Load the Excel file
    wb = load_workbook(excel_file)
    sheet = wb.active
    
    # Extract data from the sheet
    data = []
    for row in sheet.iter_rows(values_only=True):
        data.append(list(row))
    
    # Create the PDF
    pdf_file = "worker_schedule.pdf"
    document = SimpleDocTemplate(pdf_file, pagesize=letter)

    table = Table(data)

    # Set table style
    table.setStyle(TableStyle([ 
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    # Build the PDF
    elements = [table]
    document.build(elements)
    
    # Return the generated PDF for download
    return pdf_file

@app.route('/download_pdf', methods=['POST'])
def download_pdf():
    global start_date
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

    for idx, name in enumerate(schedule_data['Name']):
        row = [name]
        for i in range(7):
            day = schedule_data[list(schedule_data.keys())[i + 1]][idx]  # Get the corresponding day's shift
            row.append(day if day != "N/A" else "")
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
    app.run(host='0.0.0.0', port=8181)
