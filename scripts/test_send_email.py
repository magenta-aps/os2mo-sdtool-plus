# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from sdtoolplus.config import get_settings
from sdtoolplus.email import send_email_notification

settings = get_settings()

send_email_notification(settings, "This is a test")
