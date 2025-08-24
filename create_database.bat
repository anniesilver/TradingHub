@echo off
echo Creating TradingHub Database...
echo.

echo This will create the 'tradinghub' database
echo You'll be prompted for the postgres user password

createdb -U postgres tradinghub

if %ERRORLEVEL% == 0 (
    echo.
    echo ✓ Database 'tradinghub' created successfully!
    echo.
    echo Next steps:
    echo 1. Copy backend\services\.env.example to backend\services\.env
    echo 2. Edit .env file with your postgres password
    echo 3. Run: python backend\init_all_db.py
) else (
    echo.
    echo ✗ Database creation failed
    echo Make sure PostgreSQL is running and you have the correct password
)

pause