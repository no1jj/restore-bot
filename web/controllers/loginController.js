const sqlite3 = require('sqlite3').verbose();
const crypto = require('crypto');

/**
 * 로그인 페이지 렌더링
 */
exports.renderLoginPage = (req, res) => {
    res.render('login');
};

/**
 * 로그인 처리 로직
 */
exports.processLogin = async (req, res) => {
    const { username, password } = req.body;
    
    try {
        const config = req.app.get('config');
        const db = new sqlite3.Database(config.DBPath);
        
        db.get("SELECT * FROM WebPanel WHERE id = ?", [username], (err, row) => {
            if (err) {
                console.error('로그인 오류:', err);
                return res.status(500).render('login', { error: '로그인 중 오류가 발생했습니다.' });
            }
            
            if (!row) {
                return res.render('login', { error: '아이디 또는 비밀번호가 올바르지 않습니다.' });
            }
            
            const hashedPassword = crypto.createHash('sha256')
                                        .update(password + row.salt)
                                        .digest('hex');
            
            if (hashedPassword !== row.password) {
                return res.render('login', { error: '아이디 또는 비밀번호가 올바르지 않습니다.' });
            }
            
            req.session.loggedIn = true;
            req.session.serverId = row.serverId;
            req.session.userId = row.id;
            
            res.redirect('/setting');
        });
    } catch (error) {
        console.error('로그인 오류:', error);
        res.status(500).render('login', { error: '로그인 중 오류가 발생했습니다.' });
    }
};

/**
 * 로그아웃 처리
 */
exports.processLogout = (req, res) => {
    req.session.destroy((err) => {
        if (err) {
            console.error('로그아웃 오류:', err);
        }
        res.redirect('/');
    });
}; 