"""DB status words (FYP document) mapped to the labels Figma/screens show.

The database stores the document's words ("On the Way", "Off Duty");
templates and JSON responses show the Figma wording through these maps,
never by hard-coding a different string elsewhere.
"""

ORDER_STATUS_LABELS = {
    "Pending": "Pending",
    "Assigned": "Assigned",
    "On the Way": "On the way",
    "Delivered": "Delivered",
    "Cancelled": "Cancelled",
}

DRIVER_STATUS_LABELS = {
    "Available": "Available",
    "Busy": "Busy",
    "Off Duty": "Off duty",
}


def order_status_label(db_value):
    return ORDER_STATUS_LABELS.get(db_value, db_value)


def driver_status_label(db_value):
    return DRIVER_STATUS_LABELS.get(db_value, db_value)
