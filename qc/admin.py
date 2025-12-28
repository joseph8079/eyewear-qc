from django.contrib import admin
from .models import Store, FrameStyle, FrameVariant, Complaint, Attachment

admin.site.register(Store)
admin.site.register(FrameStyle)
admin.site.register(FrameVariant)
admin.site.register(Complaint)
admin.site.register(Attachment)
