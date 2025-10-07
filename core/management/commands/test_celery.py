from django.core.management.base import BaseCommand
from core.tasks import debug_task, send_email_task, process_data_task
import time


class Command(BaseCommand):
    help = 'Test Celery tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            choices=['debug', 'email', 'process_data', 'all'],
            default='debug',
            help='Which task to test',
        )

    def handle(self, *args, **options):
        task_type = options['task']

        self.stdout.write(self.style.SUCCESS('Testing Celery tasks...'))
        self.stdout.write('')

        if task_type in ['debug', 'all']:
            self.test_debug_task()

        if task_type in ['email', 'all']:
            self.test_email_task()

        if task_type in ['process_data', 'all']:
            self.test_process_data_task()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Task testing completed!'))

    def test_debug_task(self):
        self.stdout.write('Testing debug task...')
        
        # Execute task
        result = debug_task.delay()
        
        self.stdout.write(f'Task ID: {result.id}')
        self.stdout.write('Waiting for result...')
        
        # Wait for result (max 10 seconds)
        try:
            task_result = result.get(timeout=10)
            self.stdout.write(self.style.SUCCESS(f'✓ Debug task completed: {task_result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Debug task failed: {str(e)}'))
        
        self.stdout.write('')

    def test_email_task(self):
        self.stdout.write('Testing email task...')
        
        # Execute task
        result = send_email_task.delay(
            subject='Test Email from Celery',
            message='This is a test email sent from a Celery task.',
            recipient_list=['test@example.com']
        )
        
        self.stdout.write(f'Task ID: {result.id}')
        self.stdout.write('Waiting for result...')
        
        # Wait for result (max 10 seconds)
        try:
            task_result = result.get(timeout=10)
            self.stdout.write(self.style.SUCCESS(f'✓ Email task completed: {task_result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Email task failed: {str(e)}'))
        
        self.stdout.write('')

    def test_process_data_task(self):
        self.stdout.write('Testing data processing task...')
        
        test_data = {
            'user_id': 123,
            'action': 'test_action',
            'timestamp': time.time()
        }
        
        # Execute task
        result = process_data_task.delay(test_data)
        
        self.stdout.write(f'Task ID: {result.id}')
        self.stdout.write('Waiting for result...')
        
        # Wait for result (max 15 seconds)
        try:
            task_result = result.get(timeout=15)
            self.stdout.write(self.style.SUCCESS(f'✓ Data processing task completed'))
            self.stdout.write(f'  Result: {task_result}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Data processing task failed: {str(e)}'))
        
        self.stdout.write('')