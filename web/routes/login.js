const express = require('express');
const router = express.Router();
const csrf = require('csurf');
const { check, validationResult } = require('express-validator');
const loginController = require('../controllers/loginController');

const csrfProtection = csrf({ cookie: false });

const loginValidation = [
    check('username').notEmpty().withMessage('아이디를 입력해주세요.'),
    check('password').notEmpty().withMessage('비밀번호를 입력해주세요.')
];

router.get('/login', csrfProtection, loginController.renderLoginPage);

router.post('/login', csrfProtection, loginValidation, (req, res, next) => {
    const errors = validationResult(req);
    
    if (!errors.isEmpty()) {
        return res.render('login', {
            error: errors.array()[0].msg,
            csrfToken: req.csrfToken()
        });
    }
    
    next();
}, loginController.processLogin);

router.get('/logout', loginController.processLogout);

module.exports = router; 

// V1.2