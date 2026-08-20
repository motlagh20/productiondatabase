SELECT page_name FROM app.pages ORDER BY page_name;
SELECT username, is_active FROM app.users WHERE username='admin';
SELECT must_change_password FROM app.user_credentials c JOIN app.users u ON u.user_id=c.user_id WHERE u.username='admin';
SELECT r.role_name, COUNT(*) AS pages FROM app.role_permissions rp JOIN app.roles r ON rp.role_id=r.role_id WHERE r.role_name='Admin' GROUP BY r.role_name;
SELECT * FROM app.shifts_definition ORDER BY shift_code;

