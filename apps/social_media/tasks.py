from celery import shared_task
from django.utils import timezone
from django.core.files.base import ContentFile
from apps.social_media.models import SocialMediaPost, SocialMediaImportJob
from apps.social_media.services import TelegramService, InstagramService
import requests
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_social_media_post(self, post_id):
    """
    Process a social media post for product creation
    Product requirement: Background processing of social media imports
    """
    try:
        post = SocialMediaPost.objects.get(id=post_id)
        
        if post.is_processed:
            return f"Post {post_id} already processed"
        
        # Download and save media files
        downloaded_media = []
        for media_item in post.media_files:
            if media_item.get('url'):
                try:
                    downloaded_path = download_media_file(
                        media_item['url'],
                        media_item.get('type', 'image'),
                        post.account.store_id,
                        post.external_id
                    )
                    if downloaded_path:
                        media_item['local_path'] = downloaded_path
                        downloaded_media.append(media_item)
                except Exception as e:
                    logger.warning(f"Failed to download media {media_item['url']}: {e}")
        
        # Update post with downloaded media
        post.media_files = downloaded_media
        post.is_processed = True
        post.save(update_fields=['media_files', 'is_processed'])
        
        logger.info(f"Successfully processed social media post {post_id}")
        return f"Post {post_id} processed successfully"
        
    except SocialMediaPost.DoesNotExist:
        logger.error(f"Social media post {post_id} not found")
        return f"Post {post_id} not found"
    except Exception as exc:
        logger.error(f"Error processing social media post {post_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return f"Failed to process post {post_id} after {self.max_retries} retries"


@shared_task(bind=True, max_retries=2, default_retry_delay=120)
def import_social_media_posts(self, job_id):
    """
    Import posts from social media platforms
    Product requirement: "gets 5 last posts and stories"
    """
    try:
        job = SocialMediaImportJob.objects.get(id=job_id)
        job.status = 'running'
        job.started_at = timezone.now()
        job.current_step = 'Initializing import'
        job.save(update_fields=['status', 'started_at', 'current_step'])
        
        # Get appropriate service
        if job.account.platform == 'telegram':
            service = TelegramService(job.account)
        elif job.account.platform == 'instagram':
            service = InstagramService(job.account)
        else:
            raise ValueError(f"Unsupported platform: {job.account.platform}")
        
        # Update progress
        job.current_step = 'Fetching posts from platform'
        job.progress_percentage = 10
        job.save(update_fields=['current_step', 'progress_percentage'])
        
        # Fetch posts
        posts_data = service.fetch_recent_posts(
            max_items=job.max_items,
            since_date=job.since_date,
            include_stories=(job.job_type in ['stories', 'both'])
        )
        
        job.total_found = len(posts_data)
        job.current_step = f'Processing {job.total_found} posts'
        job.progress_percentage = 30
        job.save(update_fields=['total_found', 'current_step', 'progress_percentage'])
        
        imported_count = 0
        skipped_count = 0
        
        for i, post_data in enumerate(posts_data):
            try:
                # Check if post already exists
                existing_post = SocialMediaPost.objects.filter(
                    account=job.account,
                    external_id=post_data['external_id']
                ).first()
                
                if existing_post:
                    skipped_count += 1
                    continue
                
                # Create new post
                post = SocialMediaPost.objects.create(
                    store=job.store,
                    account=job.account,
                    external_id=post_data['external_id'],
                    post_type=post_data.get('post_type', 'post'),
                    caption=post_data.get('caption', ''),
                    hashtags=post_data.get('hashtags', []),
                    mentions=post_data.get('mentions', []),
                    media_files=post_data.get('media_files', []),
                    likes_count=post_data.get('likes_count', 0),
                    comments_count=post_data.get('comments_count', 0),
                    views_count=post_data.get('views_count', 0),
                    post_url=post_data.get('post_url', ''),
                    published_at=post_data.get('published_at'),
                    raw_data=post_data
                )
                
                # Queue background processing for media download
                process_social_media_post.delay(str(post.id))
                imported_count += 1
                
                # Update progress
                progress = 30 + (70 * (i + 1) / len(posts_data))
                job.progress_percentage = min(int(progress), 95)
                job.save(update_fields=['progress_percentage'])
                
            except Exception as e:
                logger.error(f"Error creating post {post_data.get('external_id')}: {e}")
                skipped_count += 1
        
        # Complete the job
        job.status = 'completed'
        job.total_imported = imported_count
        job.total_skipped = skipped_count
        job.progress_percentage = 100
        job.current_step = 'Import completed'
        job.completed_at = timezone.now()
        job.save(update_fields=[
            'status', 'total_imported', 'total_skipped', 
            'progress_percentage', 'current_step', 'completed_at'
        ])
        
        logger.info(f"Social media import job {job_id} completed: {imported_count} imported, {skipped_count} skipped")
        return f"Import completed: {imported_count} imported, {skipped_count} skipped"
        
    except SocialMediaImportJob.DoesNotExist:
        logger.error(f"Import job {job_id} not found")
        return f"Job {job_id} not found"
    except Exception as exc:
        # Mark job as failed
        try:
            job = SocialMediaImportJob.objects.get(id=job_id)
            job.status = 'failed'
            job.error_message = str(exc)
            job.completed_at = timezone.now()
            job.save(update_fields=['status', 'error_message', 'completed_at'])
        except:
            pass
        
        logger.error(f"Error in social media import job {job_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120 * (2 ** self.request.retries))
        return f"Failed to complete import job {job_id} after {self.max_retries} retries"


@shared_task
def cleanup_old_social_media_data():
    """
    Cleanup old social media posts and imported data
    Runs daily to maintain database performance
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=90)  # Keep 3 months of data
    
    # Delete old unprocessed posts
    old_posts = SocialMediaPost.objects.filter(
        created_at__lt=cutoff_date,
        is_imported=False,
        is_processed=True
    )
    deleted_posts_count = old_posts.count()
    old_posts.delete()
    
    # Delete old completed import jobs
    old_jobs = SocialMediaImportJob.objects.filter(
        created_at__lt=cutoff_date,
        status__in=['completed', 'failed']
    )
    deleted_jobs_count = old_jobs.count()
    old_jobs.delete()
    
    logger.info(f"Cleaned up {deleted_posts_count} old posts and {deleted_jobs_count} old import jobs")
    return f"Cleaned up {deleted_posts_count} posts and {deleted_jobs_count} jobs"


@shared_task(bind=True, max_retries=3)
def sync_social_media_account(self, account_id):
    """
    Sync social media account data (followers, posts count, etc.)
    """
    try:
        from apps.social_media.models import SocialMediaAccount
        
        account = SocialMediaAccount.objects.get(id=account_id)
        
        # Get appropriate service
        if account.platform == 'telegram':
            service = TelegramService(account)
        elif account.platform == 'instagram':
            service = InstagramService(account)
        else:
            raise ValueError(f"Unsupported platform: {account.platform}")
        
        # Fetch account info
        account_info = service.get_account_info()
        
        # Update account data
        account.followers_count = account_info.get('followers_count', 0)
        account.posts_count = account_info.get('posts_count', 0)
        account.display_name = account_info.get('display_name', account.display_name)
        account.last_sync_at = timezone.now()
        account.is_verified = account_info.get('is_verified', False)
        account.save(update_fields=[
            'followers_count', 'posts_count', 'display_name',
            'last_sync_at', 'is_verified'
        ])
        
        logger.info(f"Successfully synced social media account {account_id}")
        return f"Account {account_id} synced successfully"
        
    except Exception as exc:
        logger.error(f"Error syncing social media account {account_id}: {exc}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return f"Failed to sync account {account_id}"


def download_media_file(url, media_type, store_id, post_id):
    """
    Download media file from URL and save locally
    """
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # Determine file extension
        content_type = response.headers.get('content-type', '')
        if media_type == 'image':
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = 'jpg'
            elif 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            else:
                ext = 'jpg'  # Default
        else:  # video
            if 'mp4' in content_type:
                ext = 'mp4'
            elif 'webm' in content_type:
                ext = 'webm'
            else:
                ext = 'mp4'  # Default
        
        # Generate filename
        filename = f"social_media/{store_id}/{post_id}_{timezone.now().timestamp():.0f}.{ext}"
        
        # Save file
        from django.core.files.storage import default_storage
        file_content = ContentFile(response.content)
        saved_path = default_storage.save(filename, file_content)
        
        return saved_path
        
    except Exception as e:
        logger.error(f"Error downloading media file {url}: {e}")
        return None


# Periodic tasks registration (add to celery beat schedule)
@shared_task
def schedule_social_media_sync():
    """
    Schedule sync for all active social media accounts
    Runs every 6 hours
    """
    from apps.social_media.models import SocialMediaAccount
    
    active_accounts = SocialMediaAccount.objects.filter(
        is_active=True,
        auto_import_enabled=True
    )
    
    scheduled_count = 0
    for account in active_accounts:
        sync_social_media_account.delay(str(account.id))
        scheduled_count += 1
    
    logger.info(f"Scheduled sync for {scheduled_count} social media accounts")
    return f"Scheduled sync for {scheduled_count} accounts"


@shared_task
def auto_import_from_accounts():
    """
    Auto-import posts from accounts with auto_import_enabled
    Runs every 2 hours
    """
    from apps.social_media.models import SocialMediaAccount, SocialMediaImportJob
    
    auto_import_accounts = SocialMediaAccount.objects.filter(
        is_active=True,
        auto_import_enabled=True
    )
    
    scheduled_count = 0
    for account in auto_import_accounts:
        # Check if there's already a running job for this account
        existing_job = SocialMediaImportJob.objects.filter(
            account=account,
            status__in=['pending', 'running']
        ).first()
        
        if not existing_job:
            # Create new import job
            job = SocialMediaImportJob.objects.create(
                store=account.store,
                account=account,
                job_type='posts',
                max_items=5,  # As per product requirement
                since_date=timezone.now() - timezone.timedelta(hours=2)
            )
            
            # Queue the import
            import_social_media_posts.delay(str(job.id))
            scheduled_count += 1
    
    logger.info(f"Scheduled auto-import for {scheduled_count} accounts")
    return f"Scheduled auto-import for {scheduled_count} accounts"
