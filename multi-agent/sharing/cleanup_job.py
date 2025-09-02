#!/usr/bin/env python3
"""
Cleanup job for old share invitations.
Can be run as a cron job or scheduled task.
"""

import sys
import argparse
from datetime import datetime

def run_share_cleanup(dry_run: bool = False, verbose: bool = False):
    """Background job to cleanup old invites."""
    try:
        from core.app_container import AppContainer
        from config.app_config import AppConfig
        from sharing.models import ShareCleanupConfig
        
        # Initialize container
        config = AppConfig.get_instance()
        container = AppContainer(config)
        
        if verbose:
            print(f"🧹 Starting share cleanup at {datetime.utcnow()}")
            print(f"📊 Dry run mode: {dry_run}")
        
        # Get cleanup stats first
        stats = container.share_service.get_cleanup_stats(days_back=30)
        if verbose:
            print(f"📈 Cleanup stats (last 30 days):")
            for key, value in stats.items():
                print(f"  - {key}: {value}")
        
        # Configure cleanup
        cleanup_config = ShareCleanupConfig(
            pending_days=10,    # Delete old pending after 10 days
            declined_days=7,    # Delete declined after 7 days  
            canceled_days=7,    # Delete canceled after 7 days
            expired_days=1,     # Delete expired after 1 day
            dry_run=dry_run,
            batch_size=1000
        )
        
        # Run cleanup
        result = container.share_service.cleanup_old_invites(cleanup_config)
        
        if verbose:
            print(f"🔥 Cleanup result:")
            print(f"  - Total processed: {result.total_processed}")
            print(f"  - Deleted: {result.deleted_count}")
            print(f"  - Pending: {result.pending_count}")
            print(f"  - Declined: {result.declined_count}")
            print(f"  - Canceled: {result.canceled_count}")
            print(f"  - Errors: {result.errors}")
        
        # Also cleanup expired invites
        expired_result = container.share_service.cleanup_expired_invites(dry_run=dry_run)
        
        if verbose:
            print(f"⏰ Expired cleanup result:")
            print(f"  - Expired deleted: {expired_result.expired_count}")
            print(f"  - Errors: {expired_result.errors}")
        
        total_deleted = result.deleted_count + expired_result.deleted_count
        
        if verbose:
            print(f"✅ Cleanup completed. Total deleted: {total_deleted}")
        
        return total_deleted
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return -1

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Cleanup old share invitations")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be deleted without actually deleting")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--quiet", "-q", action="store_true",
                       help="Quiet mode (no output)")
    
    args = parser.parse_args()
    
    if args.quiet and args.verbose:
        print("Error: Cannot use both --quiet and --verbose")
        sys.exit(1)
    
    deleted_count = run_share_cleanup(
        dry_run=args.dry_run, 
        verbose=args.verbose and not args.quiet
    )
    
    if not args.quiet:
        if args.dry_run:
            print(f"Would delete {deleted_count} invitations")
        else:
            print(f"Deleted {deleted_count} old invitations")
    
    sys.exit(0 if deleted_count >= 0 else 1)

if __name__ == "__main__":
    main()
