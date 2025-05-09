const express = require('express');
const router = express.Router();
const csrf = require('csurf');
const { check, validationResult } = require('express-validator');
const settingController = require('../controllers/settingController');
const infoRouter = require('./info');
const setupRouter = require('./setup');
const customLinkRouter = require('./customLink');
const linkPageController = require('../controllers/linkPageController');

const csrfProtection = csrf({ cookie: false });

const authMiddleware = (req, res, next) => {
    if (!req.session.loggedIn) {
        req.flash('error', '로그인이 필요한 페이지입니다.');
        return res.redirect('/login');
    }
    next();
};

const settingsValidation = [
    check('webhookUrl')
        .optional({ nullable: true, checkFalsy: true })
        .isURL()
        .withMessage('유효한 웹훅 URL을 입력해주세요.'),
    check('roleId')
        .optional({ nullable: true, checkFalsy: true })
        .isNumeric()
        .withMessage('역할 ID는 숫자만 입력 가능합니다.'),
    check('loggingChannelId')
        .optional({ nullable: true, checkFalsy: true })
        .isNumeric()
        .withMessage('채널 ID는 숫자만 입력 가능합니다.')
];

router.get('/', authMiddleware, csrfProtection, settingController.renderSettingPage);

router.post('/update', authMiddleware, csrfProtection, settingsValidation, (req, res, next) => {
    const errors = validationResult(req);
    
    if (!errors.isEmpty()) {
        req.flash('error', errors.array()[0].msg);
        return res.redirect('/setting');
    }
    
    next();
}, settingController.updateSettings);

router.get('/stats', authMiddleware, settingController.getServerStats);

router.use('/info', infoRouter);
router.use('/setup', setupRouter);
router.use('/link', customLinkRouter);

router.get('/link_page', authMiddleware, csrfProtection, linkPageController.renderLinkPage);

module.exports = router; 

// V1.5