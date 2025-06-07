import smtplib
from email.message import EmailMessage
import ssl

email_recipients=['keerthiruban6194@gmail.com']
#your email login
email="srijeyam23@gmail.com"
password="yddzolpmcaaieqsk"
body="Hai,signed in successfully."

msg=EmailMessage()
msg['subject']="confirmation Mail"
msg['From']=email
msg['To']="jeyashree236@gmail.com"
msg.set_content(body)

context=ssl.create_default_context()

try:
    with smtplib.SMTP('smtp.gmail.com',587) as server:
      server.starttls(context=context) 
      server.login(email,password)
      server.send_message(msg)
      server.quit()
    print("email send")
except Exception as e:
    print("email error",e)
