import os
import re
from datetime import datetime
from flask import Flask, render_template, request, send_file, abort
import pandas as pd

# ReportLab layout engine for generating precise PDFs
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = Flask(__name__)

# Dynamically links to your local directory uploads folder safely on Arch Linux
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def parse_exam_session_string(session_val):
    """Transforms codes like '2026-JUNE' into 'TEE June 2026'."""
    if pd.isna(session_val):
        return "TEE Examination"
    val_str = str(session_val).strip()
    match = re.match(r"(\d{4})[-_ ]([a-zA-Z]+)", val_str)
    if match:
        year, month = match.group(1), match.group(2)
        return f"TEE {month.capitalize()} {year}"
    return f"TEE {val_str}"

def format_date_for_filename(date_val):
    """Converts varying date structural text blocks into clean DD-MM-YY layouts."""
    if pd.isna(date_val):
        return "UNKNOWN_DATE"
    date_str = str(date_val).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y'):
        try:
            dt = datetime.strptime(date_str.split()[0], fmt)
            return dt.strftime('%d-%m-%y')
        except ValueError:
            continue
    return date_str.replace('/', '-')

def get_session_abbreviation(session_val):
    """Maps Evening/Afternoon slots cleanly to AN, and Morning slots to FN."""
    if pd.isna(session_val):
        return "SESSION"
    s_str = str(session_val).strip().upper()
    if "EVENING" in s_str or "AN" in s_str or "AFTERNOON" in s_str:
        return "AN"
    if "MORNING" in s_str or "FN" in s_str:
        return "FN"
    return s_str

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file uploaded.", 400
    file = request.files['file']
    if file.filename == '':
        return "No selected file.", 400

    if file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        # Handle sheet formatting types
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df.columns = df.columns.str.strip()
        if df.empty:
            return "The uploaded file contains no data.", 400

        # Extract top row cell metadata values safely
        sample_row = df.iloc[0]
        raw_date = sample_row.get('ExDate', 'UNKNOWN')
        raw_session = sample_row.get('Session', 'UNKNOWN')
        raw_exam_session = sample_row.get('Exam Session', 'UNKNOWN')

        formatted_date = format_date_for_filename(raw_date)
        session_abbr = get_session_abbreviation(raw_session)
        tee_title = parse_exam_session_string(raw_exam_session)

        # Dynamic Output Naming Strings
        attendance_filename = f"ATTENDANCE {formatted_date} {session_abbr}.pdf"
        absentee_filename = f"ABSENTEE {formatted_date} {session_abbr}.pdf"

        attendance_path = os.path.join(app.config['UPLOAD_FOLDER'], attendance_filename)
        absentee_path = os.path.join(app.config['UPLOAD_FOLDER'], absentee_filename)

        df['Course'] = df['Course'].astype(str).str.strip()
        unique_courses = sorted(df['Course'].unique())

        # ==========================================
        # BUILD FILE 1: LANDSCAPE ATTENDANCE PDF (MAX ROWS COMPACT LAYOUT)
        # ==========================================
        atten_doc = SimpleDocTemplate(
            attendance_path, 
            pagesize=landscape(letter),
            rightMargin=25, leftMargin=25, topMargin=15, bottomMargin=15
        )
        atten_story = []
        styles = getSampleStyleSheet()

        cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=7, leading=9)
        header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=8, leading=10, fontName='Helvetica-Bold', textColor=colors.white)

        for i, course in enumerate(unique_courses):
            course_df = df[df['Course'] == course].copy()
            
            title_text = f"<b>{tee_title} - Attendance Sheet</b><br/>Course: {course} &nbsp;&nbsp;|&nbsp;&nbsp; Date: {raw_date} &nbsp;&nbsp;|&nbsp;&nbsp; Session: {raw_session}"
            atten_story.append(Paragraph(title_text, styles['Heading3']))
            atten_story.append(Spacer(1, 8))

            table_data = [[
                Paragraph("<b>SNo</b>", header_style),
                Paragraph("<b>Enrollment No</b>", header_style),
                Paragraph("<b>Name of Candidate</b>", header_style),
                Paragraph("<b>Course</b>", header_style),
                Paragraph("<b>Centre</b>", header_style),
                Paragraph("<b>Status</b>", header_style),
                Paragraph("<b>Exam Date</b>", header_style),
                Paragraph("<b>Session</b>", header_style),
                Paragraph("<b>User ID</b>", header_style),
                Paragraph("<b>IP Address</b>", header_style),
                Paragraph("<b>Timestamp</b>", header_style),
                Paragraph("<b>Exam Session</b>", header_style)
            ]]

            sno = 1
            for _, row in course_df.iterrows():
                table_data.append([
                    Paragraph(str(sno), cell_style),
                    Paragraph(str(row.get('Enrno', '')), cell_style),
                    Paragraph(str(row.get('Name', '')), cell_style),
                    Paragraph(str(row.get('Course', '')), cell_style),
                    Paragraph(str(row.get('Centre', '')), cell_style),
                    Paragraph(str(row.get('Attendance', '')), cell_style),
                    Paragraph(str(row.get('ExDate', '')), cell_style),
                    Paragraph(str(row.get('Session', '')), cell_style),
                    Paragraph(str(row.get('UserId', '')), cell_style),
                    Paragraph(str(row.get('IPAdd', '')), cell_style),
                    Paragraph(str(row.get('tm_stmp', '')), cell_style),
                    Paragraph(str(row.get('Exam Session', '')), cell_style),
                ])
                sno += 1

            col_widths = [22, 60, 110, 48, 38, 48, 55, 60, 38, 72, 85, 66]
            t = Table(table_data, colWidths=col_widths, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a8a')),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            atten_story.append(t)

            if i < len(unique_courses) - 1:
                atten_story.append(PageBreak())

        atten_doc.build(atten_story)

        # ==========================================
        # BUILD FILE 2: PORTRAIT ABSENTEE PDF
        # ==========================================
        abs_doc = SimpleDocTemplate(
            absentee_path, 
            pagesize=letter,
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
        )
        abs_story = []
        
        title_style = ParagraphStyle('AbsTitle', fontName='Helvetica-Bold', fontSize=14, leading=16, alignment=1)
        meta_label_style = ParagraphStyle('AbsMetaLabel', fontName='Helvetica-Bold', fontSize=10, leading=13)
        meta_value_style = ParagraphStyle('AbsMetaVal', fontName='Helvetica', fontSize=10, leading=15)
        
        abs_header_style = ParagraphStyle('AbsHdr', fontName='Helvetica-Bold', fontSize=9, leading=11, alignment=1)
        abs_cell_center = ParagraphStyle('AbsCellC', fontName='Helvetica', fontSize=9, leading=12, alignment=1)
        nil_style = ParagraphStyle('AbsNil', fontName='Helvetica-Bold', fontSize=48, leading=56, alignment=1, textColor=colors.black)

        for i, course in enumerate(unique_courses):
            course_df = df[df['Course'] == course]
            
            absent_df = course_df[course_df['Attendance'].astype(str).str.upper() == 'ABSENT']
            absent_count = len(absent_df)

            # 1. Official Institutional Main Title Header
            abs_story.append(Paragraph(f"<b>INDIRA GANDHI NATIONAL OPEN UNIVERSITY</b>", title_style))
            abs_story.append(Paragraph(f"<b>MAIDAN GARHI, NEW DELHI – 110068</b>", title_style))
            abs_story.append(Paragraph(f"<b>STUDENT ABSENTEES STATEMENT</b>", title_style))
            abs_story.append(Spacer(1, 15))

            # 2. Structural Metadata Information Grid Box
            meta_table_data = [
                [
                    Paragraph("<b>Exam:</b>", meta_label_style), Paragraph(str(tee_title), meta_value_style),
                    Paragraph("<b>Date:</b>", meta_label_style), Paragraph(f"{formatted_date} {session_abbr}", meta_value_style)
                ],
                [
                    Paragraph("<b>Course Code:</b>", meta_label_style), Paragraph(str(course), meta_value_style),
                    Paragraph("", meta_label_style), Paragraph("", meta_value_style)
                ]
            ]
            meta_table = Table(meta_table_data, colWidths=[90, 170, 90, 180])
            meta_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            abs_story.append(meta_table)
            abs_story.append(Spacer(1, 15))

            # 3. Conditional Content Output Branching Strategy
            if absent_count == 0:
                abs_story.append(Spacer(1, 40))
                abs_story.append(Paragraph("NIL", nil_style))
                abs_story.append(Spacer(1, 60))
            else:
                abs_table_data = [[
                    Paragraph("<b>SL No</b>", abs_header_style),
                    Paragraph("<b>Enrollment No</b>", abs_header_style),
                    Paragraph("<b>SL No</b>", abs_header_style),
                    Paragraph("<b>Enrollment No</b>", abs_header_style),
                    Paragraph("<b>SL No</b>", abs_header_style),
                    Paragraph("<b>Enrollment No</b>", abs_header_style)
                ]]

                rows_needed = 20
                abs_list = list(absent_df['Enrno'].dropna().astype(str))
                
                for r in range(rows_needed):
                    idx1 = r
                    idx2 = r + 20
                    idx3 = r + 40
                    
                    val1 = abs_list[idx1] if idx1 < len(abs_list) else ""
                    val2 = abs_list[idx2] if idx2 < len(abs_list) else ""
                    val3 = abs_list[idx3] if idx3 < len(abs_list) else ""
                    
                    # Core Math Fix: Keeps counting continuous relative to column lines
                    sl_col1 = r + 1   # 1 to 20
                    sl_col2 = r + 21  # 21 to 40
                    sl_col3 = r + 41  # 41 to 60
                    
                    abs_table_data.append([
                        Paragraph(str(sl_col1), abs_cell_center),
                        Paragraph(val1, abs_cell_center),
                        Paragraph(str(sl_col2), abs_cell_center),
                        Paragraph(val2, abs_cell_center),
                        Paragraph(str(sl_col3), abs_cell_center),
                        Paragraph(val3, abs_cell_center)
                    ])

                t_abs = Table(abs_table_data, colWidths=[40, 136, 40, 136, 40, 138], repeatRows=1)
                t_abs.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('TOPPADDING', (0,0), (-1,-1), 4),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ]))
                abs_story.append(t_abs)
                abs_story.append(Spacer(1, 20))

            # 4. Signatures and Official Seals block
            sig_text = """
            <br/><br/>
            <b>Signature of the Centre Superintendent</b><br/><br/>
            Signature: __________________________<br/><br/>
            Name: _____________________________<br/><br/>
            Exam Centre Seal
            """
            abs_story.append(Paragraph(sig_text, meta_value_style))

            if i < len(unique_courses) - 1:
                abs_story.append(PageBreak())

        abs_doc.build(abs_story)

        return f"""
        <html>
        <head><title>Processing Completed</title>
        <style>
            body {{ font-family: sans-serif; background-color: #f4f6f9; padding: 40px; text-align: center; }}
            .box {{ max-width: 500px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); }}
            a {{ display: inline-block; margin: 10px 0; color: #2563eb; font-weight: bold; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .back-btn {{ margin-top: 20px; background: #64748b; color: white; padding: 10px; border-radius: 4px; display: block; text-decoration: none; }}
        </style>
        </head>
        <body>
            <div class="box">
                <h2>Files Generated Successfully!</h2>
                <p>The system has split the records for {len(unique_courses)} distinct course sheets.</p>
                <hr style="border:0; border-top:1px solid #eee; margin:20px 0;"/>
                <a href="/download/{attendance_filename}" target="_blank">📥 Download Landscape Attendance PDF</a><br/>
                <a href="/download/{absentee_filename}" target="_blank">📥 Download Portrait Absentee PDF</a>
                <a href="/" class="back-btn">Go Back</a>
            </div>
        </body>
        </html>
        """

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return abort(404, description="Target document file layer was not found.")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7860))
    app.run(host='0.0.0.0', port=port)