"""
Sample Document Generator for RAGX Phase 1 & Phase 2 Testing
"""
from pathlib import Path
import shutil
import pymupdf as fitz

def generate_sample_pdf():
    output_dir = Path(__file__).resolve().parent.parent / "data" / "uploads"
    output_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = output_dir / "Attendance_Policy.pdf"
    temp_path = output_dir / "temp_Attendance_Policy.pdf"

    if temp_path.exists():
        temp_path.unlink()

    doc = fitz.open()

    # Page 1
    page1 = doc.new_page()
    text_page1 = (
        "COLLEGE OF ENGINEERING & TECHNOLOGY\n"
        "ACADEMIC POLICY MANUAL — SECTION 4: ATTENDANCE RULES\n\n"
        "1. GENERAL ATTENDANCE REQUIREMENT:\n"
        "All undergraduate and postgraduate students enrolled in degree programs must maintain a minimum attendance of 75% in every course module during a semester.\n\n"
        "2. CONDONATION CLAUSE:\n"
        "Students having attendance between 65% and 74% due to medical reasons or valid institutional representation may apply for condonation upon submitting official certificates.\n"
        "Students with attendance below 65% are strictly not permitted to sit for final semester examinations."
    )
    page1.insert_textbox(fitz.Rect(50, 50, 550, 750), text_page1, fontsize=10)

    # Page 2
    page2 = doc.new_page()
    text_page2 = (
        "COLLEGE OF ENGINEERING & TECHNOLOGY\n"
        "ACADEMIC POLICY MANUAL — SECTION 5: GRADING & EXAMINATIONS\n\n"
        "3. CONTINUOUS INTERNAL EVALUATION (CIE):\n"
        "Internal assessments carry 40% weightage of the total grade. A student must score at least 40% in internal marks to qualify for the end-semester examination.\n\n"
        "4. GRADING SYSTEM:\n"
        "Letter grades are awarded based on relative performance:\n"
        "Grade O: Outstanding (>= 90%)\n"
        "Grade A+: Excellent (80% - 89%)\n"
        "Grade A: Very Good (70% - 79%)\n"
        "Grade B+: Good (60% - 69%)\n"
        "Grade F: Fail (< 40%)"
    )
    page2.insert_textbox(fitz.Rect(50, 50, 550, 750), text_page2, fontsize=10)

    doc.save(str(temp_path))
    doc.close()

    shutil.move(str(temp_path), str(pdf_path))
    print(f"Sample PDF created successfully at: {pdf_path}")

if __name__ == "__main__":
    generate_sample_pdf()
