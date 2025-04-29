const express = require('express');
const router = express.Router();
const authController = require('../controllers/authController');

router.get('/', authController.handleAuthCallback);
router.post('/', authController.handleAuthCallback);

module.exports = router; 