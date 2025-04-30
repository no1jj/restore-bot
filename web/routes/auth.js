const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');
const loginController = require('../controllers/loginController');

router.get('/', authController.handleAuthCallback);
router.post('/', authController.handleAuthCallback);

router.get('/login', loginController.renderLoginPage);
router.post('/login', loginController.processLogin);
router.get('/logout', loginController.processLogout);

module.exports = router;

// V1.1