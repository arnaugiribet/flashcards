from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import UserPlan
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_plan(sender, instance, created, **kwargs):
    if created:  # Only create a UserPlan if the User is newly created
        UserPlan.objects.create(user=instance)
