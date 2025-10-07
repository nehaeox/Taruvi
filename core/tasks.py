from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.mail import send_mail
from django.conf import settings
import time

logger = get_task_logger(__name__)


@shared_task
def debug_task():
    """
    A simple debug task for testing Celery setup
    """
    logger.info("Debug task executed successfully!")
    return "Debug task completed"


@shared_task
def send_email_task(subject, message, recipient_list):
    """
    Send email asynchronously using Celery
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        logger.info(f"Email sent successfully to {recipient_list}")
        return f"Email sent to {len(recipient_list)} recipients"
    except Exception as exc:
        logger.error(f"Error sending email: {exc}")
        raise exc


@shared_task
def process_data_task(data):
    """
    Process data asynchronously - example background task
    """
    logger.info(f"Processing data: {data}")
    
    # Simulate some processing time
    time.sleep(2)
    
    # Process the data (placeholder logic)
    processed_data = {
        'original': data,
        'processed_at': time.time(),
        'status': 'completed'
    }
    
    logger.info("Data processing completed")
    return processed_data


@shared_task(bind=True, max_retries=3)
def retry_task_example(self, data):
    """
    Example task with retry functionality
    """
    try:
        # Simulate a task that might fail
        if data.get('should_fail'):
            raise Exception("Task failed intentionally")
        
        logger.info(f"Task executed successfully with data: {data}")
        return {'status': 'success', 'data': data}
        
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def cleanup_old_data():
    """
    Periodic task for data cleanup - can be scheduled with Celery Beat
    """
    logger.info("Starting cleanup of old data...")
    
    # Add your cleanup logic here
    # For example: delete old log entries, temporary files, etc.
    
    logger.info("Data cleanup completed")
    return "Cleanup task completed"


# Organization-related async tasks

@shared_task(bind=True, max_retries=3)
def send_organization_invitation_email(self, invitation_id):
    """
    Send organization invitation email asynchronously
    """
    try:
        from .models import OrganizationInvitation
        
        invitation = OrganizationInvitation.objects.get(id=invitation_id)
        
        # Check if invitation is still valid
        if not invitation.is_valid():
            logger.warning(f"Attempted to send email for invalid invitation {invitation_id}")
            return "Invitation no longer valid"
        
        # Send the invitation email
        invitation.send_invitation_email()
        
        logger.info(f"Organization invitation email sent to {invitation.email} for {invitation.organization.name}")
        return f"Invitation email sent to {invitation.email}"
        
    except OrganizationInvitation.DoesNotExist:
        logger.error(f"OrganizationInvitation {invitation_id} does not exist")
        return f"Invitation {invitation_id} not found"
    except Exception as exc:
        logger.error(f"Failed to send invitation email for {invitation_id}: {exc}")
        
        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        else:
            logger.error(f"Max retries reached for invitation email {invitation_id}")
            raise exc


@shared_task
def send_organization_welcome_email(member_id):
    """
    Send welcome email when user joins organization
    """
    try:
        from .models import OrganizationMember
        from django.template.loader import render_to_string
        from django.core.mail import send_mail
        
        member = OrganizationMember.objects.select_related('organization', 'user').get(id=member_id)
        
        # Context for email templates
        context = {
            'member': member,
            'organization': member.organization,
            'user': member.user,
        }
        
        # For now, send a simple welcome email (you can create templates later)
        subject = f"Welcome to {member.organization.name}!"
        message = f"""
        Hi {member.user.get_full_name() or member.user.username},
        
        Welcome to {member.organization.name}! You've successfully joined as a {member.role}.
        
        You can now access the organization's resources and collaborate with other members.
        
        Best regards,
        The Taruvi Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member.user.email],
            fail_silently=False
        )
        
        logger.info(f"Welcome email sent to {member.user.email} for organization {member.organization.name}")
        return f"Welcome email sent to {member.user.email}"
        
    except OrganizationMember.DoesNotExist:
        logger.error(f"OrganizationMember {member_id} does not exist")
        return f"Member {member_id} not found"
    except Exception as exc:
        logger.error(f"Failed to send welcome email for member {member_id}: {exc}")
        raise exc


@shared_task
def cleanup_expired_invitations():
    """
    Clean up expired organization invitations
    """
    from django.utils import timezone
    from .models import OrganizationInvitation
    
    try:
        expired_count = OrganizationInvitation.objects.filter(
            is_accepted=False,
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        logger.info(f"Cleaned up {expired_count} expired invitations")
        return f"Cleaned up {expired_count} expired invitations"
        
    except Exception as exc:
        logger.error(f"Failed to cleanup expired invitations: {exc}")
        raise exc


@shared_task
def send_organization_notification_email(user_id, subject, message, organization_id=None):
    """
    Send notification emails to organization members
    """
    try:
        from django.contrib.auth.models import User
        from .models import Organization
        
        user = User.objects.get(id=user_id)
        
        # Add organization context if provided
        context_message = message
        if organization_id:
            organization = Organization.objects.get(id=organization_id)
            context_message = f"Organization: {organization.name}\n\n{message}"
        
        send_mail(
            subject=subject,
            message=context_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        
        logger.info(f"Notification email sent to {user.email}: {subject}")
        return f"Notification sent to {user.email}"
        
    except (User.DoesNotExist, Organization.DoesNotExist) as exc:
        logger.error(f"User or Organization not found: {exc}")
        return str(exc)
    except Exception as exc:
        logger.error(f"Failed to send notification email: {exc}")
        raise exc