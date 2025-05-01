const axios = require('axios');
const crypto = require('crypto');
const ipService = require('../services/ipService');

/**
 * 랜덤 문자열 생성
 * @param {number} length - 생성할 문자열 길이
 * @returns {string} 생성된 랜덤 문자열
 */
exports.generateRandomString = (length) => {
    const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let result = '';
    const charactersLength = characters.length;
    
    for (let i = 0; i < length; i++) {
        result += characters.charAt(Math.floor(Math.random() * charactersLength));
    }
    
    return result;
};

/**
 * User-Agent 문자열 파싱
 * @param {string} userAgent - User-Agent 문자열
 * @returns {object} OS 및 브라우저 정보
 */
exports.parseUserAgent = (userAgent) => {
    let OS = '알 수 없음';
    let Browser = '알 수 없음';
    
    if (!userAgent) {
        return { OS, Browser };
    }
    
    // OS 감지
    if (userAgent.includes('Windows')) {
        OS = 'Windows';
    } else if (userAgent.includes('Mac OS')) {
        OS = 'macOS';
    } else if (userAgent.includes('Android')) {
        OS = 'Android';
    } else if (userAgent.includes('iOS') || userAgent.includes('iPhone') || userAgent.includes('iPad')) {
        OS = 'iOS';
    } else if (userAgent.includes('Linux')) {
        OS = 'Linux';
    }
    
    // 브라우저 감지
    if (userAgent.includes('Chrome') && !userAgent.includes('Edg') && !userAgent.includes('OPR') && !userAgent.includes('Samsung')) {
        Browser = 'Chrome';
    } else if (userAgent.includes('Firefox') && !userAgent.includes('Seamonkey')) {
        Browser = 'Firefox';
    } else if (userAgent.includes('Safari') && !userAgent.includes('Chrome') && !userAgent.includes('Chromium')) {
        Browser = 'Safari';
    } else if (userAgent.includes('Edg')) {
        Browser = 'Edge';
    } else if (userAgent.includes('OPR') || userAgent.includes('Opera')) {
        Browser = 'Opera';
    } else if (userAgent.includes('MSIE') || userAgent.includes('Trident/')) {
        Browser = 'Internet Explorer';
    } else if (userAgent.includes('Samsung')) {
        Browser = 'Samsung Browser';
    }
    
    return { OS, Browser };
};

/**
 * 캡차 검증
 * @param {string} captchaResponse - 캡차 응답
 * @param {object} config - 앱 설정
 * @returns {boolean} 검증 성공 여부
 */
exports.verifyCaptcha = async (captchaResponse, config) => {
    try {
        const secretKey = config.hCaptchaSecretKey;
        if (!secretKey) {
            return false;
        }
        
        const formData = new URLSearchParams({
            secret: secretKey,
            response: captchaResponse
        });
        
        const response = await axios.post('https://hcaptcha.com/siteverify', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
        
        return response.data && response.data.success === true;
    } catch (error) {
        console.error('캡차 검증 실패:', error);
        return false;
    }
};

/**
 * VPN 사용 여부 확인
 * @param {string} ip - IP 주소
 * @param {object} config - 앱 설정
 * @returns {boolean} VPN 사용 여부
 */
exports.checkIsVpn = async (ip, config) => {
    return await ipService.checkIsVpn(ip, config);
};

// V1.2