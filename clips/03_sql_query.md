-- MySQL 查詢範例：取得近30日活躍用戶

SELECT 
    u.user_id, 
    u.username, 
    COUNT(l.login_id) as login_count,
    MAX(l.login_time) as last_login
FROM 
    users u
LEFT JOIN 
    login_logs l ON u.user_id = l.user_id
WHERE 
    u.status = 'active'
    AND l.login_time >= DATE_SUB(CURRENT_DATE, INTERVAL 30 DAY)
GROUP BY 
    u.user_id, 
    u.username
HAVING 
    login_count > 5
ORDER BY 
    last_login DESC;
