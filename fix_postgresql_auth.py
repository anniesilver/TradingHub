"""Fix PostgreSQL authentication for initial setup"""
import shutil
import os

def fix_postgresql_auth():
    """Temporarily change PostgreSQL authentication to trust for setup"""
    
    pg_hba_path = r"C:\Program Files\PostgreSQL\17\data\pg_hba.conf"
    pg_hba_backup = pg_hba_path + ".backup"
    
    try:
        # Create backup
        shutil.copy(pg_hba_path, pg_hba_backup)
        print(f"✓ Created backup: {pg_hba_backup}")
        
        # Read the file
        with open(pg_hba_path, 'r') as f:
            content = f.read()
        
        # Replace scram-sha-256 with trust for local connections
        content = content.replace('scram-sha-256', 'trust')
        
        # Write back
        with open(pg_hba_path, 'w') as f:
            f.write(content)
        
        print("✓ Changed authentication method to 'trust'")
        print("\n⚠️  IMPORTANT: You need to restart PostgreSQL service:")
        print("   Run: net stop postgresql-x64-17 && net start postgresql-x64-17")
        print("\n   Or use Services.msc to restart the PostgreSQL service")
        print("\n   After setup, restore the backup for security!")
        
        return True
        
    except PermissionError:
        print("✗ Permission denied. You need to run this as Administrator")
        print("  Right-click Command Prompt -> 'Run as Administrator'")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    fix_postgresql_auth()