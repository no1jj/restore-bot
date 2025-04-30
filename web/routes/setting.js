const express = require('express');
const router = express.Router();
const settingController = require('../controllers/settingController');

const authMiddleware = (req, res, next) => {
    if (!req.session.loggedIn) {
        return res.redirect('/login');
    }
    next();
};

router.get('/', authMiddleware, settingController.renderSettingPage);
router.post('/update', authMiddleware, settingController.updateSettings);

module.exports = router; 