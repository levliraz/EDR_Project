import re

def check_fields(f_name, email, password, val_password, message_widget):
    valid_endings = (".com", ".co.il", ".net", ".org")

    # שדה ריק
    if not f_name or not email or not password or not val_password:
        message_widget.SetLabel("השדה ריק, יש להכניס ערך")
        return False

    # שם לא תקין
    if len(f_name) < 3 or len(f_name) > 10:
        message_widget.SetLabel("השם באורך לא תקין")
        return False

    # אימייל – חייב להכיל @
    if "@" not in email:
        message_widget.SetLabel("באמייל חייב להיות התו @")
        return False

    # אימייל – סיומת תקינה
    if not email.endswith(valid_endings):
        message_widget.SetLabel("אימייל חייב להסתיים בסיומת תקנית")
        return False

    # אימייל – חייב לכלול gmail
    if "gmail" not in email:
        message_widget.SetLabel("אימייל חייב להכיל את המילה gmail")
        return False

    if "@gmail" not in email:
        message_widget.SetLabel("באמייל חייב להופיע @gmail לפי הסדר")
        return False

    # סיסמה – אות גדולה
    if not re.search(r'[A-Z]', password):
        message_widget.SetLabel("בסיסמא חייבת להיות לפחות אות גדולה")
        return False

    # סיסמה – אות קטנה
    if not re.search(r'[a-z]', password):
        message_widget.SetLabel("בסיסמא חייבת להיות לפחות אות קטנה")
        return False

    # סיסמה – מספר
    if not re.search(r'\d', password):
        message_widget.SetLabel("בסיסמא חייב להיות לפחות מספר")
        return False

    # סיסמה – תו מיוחד
    if not re.search(r'[!@#$%^&*]', password):
        message_widget.SetLabel("הסיסמא חייבת להכיל תו מיוחד")
        return False

    # סיסמה – אורך
    if len(password) < 4:
        message_widget.SetLabel("סיסמא חייבת להיות באורך גדול מ-4 תווים")
        return False

    # סיסמה – אימות
    if password != val_password:
        message_widget.SetLabel("אימות הסיסמא נכשל, נסה שוב")
        return False

    # אם הכול תקין
    message_widget.SetLabel("")
    return True
