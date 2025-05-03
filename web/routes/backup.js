const express = require('express');
const router = express.Router();
const csrf = require('csurf');
const backupController = require('../controllers/backupController');

const csrfProtection = csrf({ cookie: false });

const authMiddleware = (req, res, next) => {
    if (!req.session.loggedIn) {
        req.flash('error', '로그인이 필요한 페이지입니다.');
        return res.redirect('/login');
    }
    next();
};

router.get('/', authMiddleware, csrfProtection, backupController.renderBackupPage);

router.post('/create', authMiddleware, csrfProtection, backupController.createBackup);

router.get('/list', authMiddleware, csrfProtection, backupController.getBackupList);

router.get('/details/:path', authMiddleware, csrfProtection, backupController.getBackupDetails);

router.post('/delete', authMiddleware, csrfProtection, backupController.deleteBackup);

module.exports = router;

// V1.4