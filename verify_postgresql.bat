@echo off
echo Verifying PostgreSQL Installation...
echo.

echo 1. Checking PostgreSQL service...
sc query postgresql-x64-16
echo.

echo 2. Checking if psql is in PATH...
where psql
echo.

echo 3. Testing PostgreSQL connection (will prompt for password)...
echo Use the password you set during installation
psql -U postgres -c "SELECT version();"
echo.

echo 4. If successful, PostgreSQL is ready!
pause