import win32com.client as win32


def send_email_from_application(recipients, subject, body):
    # Create an Outlook application instance
    outlook = win32.Dispatch("Outlook.Application")

    # Create a new mail item
    mail = outlook.CreateItem(0)

    # Set the email parameters
    mail.To = recipients
    mail.Subject = subject

    # Set the HTML body of the email
    mail.HTMLBody = body

    # Display the email in Outlook (opens a new window)
    mail.Display()
