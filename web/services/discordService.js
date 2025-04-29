const axios = require('axios');

/**
 * 디스코드 인증 토큰 교환
 * @param {string} code - 인증 코드
 * @param {object} config - 앱 설정
 * @returns {object|null} 토큰 정보 또는 실패 시 null
 */
exports.exchangeToken = async (code, config) => {
    try {
        const redirectUri = `${config.domain}/verify`;
        
        const formData = new URLSearchParams({
            client_id: String(config.clientId),
            client_secret: config.clientSecret,
            grant_type: 'authorization_code',
            code: code,
            redirect_uri: redirectUri
        });
        
        let response;
        let retryCount = 0;
        const maxRetries = 3;
        
        while (retryCount < maxRetries) {
            try {
                response = await axios.post('https://discord.com/api/v10/oauth2/token', formData, {
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded'
                    },
                    timeout: 10000
                });
                break;
            } catch (requestError) {
                if (requestError.response && requestError.response.status === 429) {
                    const retryAfter = requestError.response.data.retry_after || 5;
                    await new Promise(resolve => setTimeout(resolve, (retryAfter + 1) * 1000));
                    retryCount++;
                } else {
                    console.error('토큰 교환 실패:', requestError.message);
                    throw requestError;
                }
            }
        }
        
        if (retryCount >= maxRetries) {
            return null;
        }
        
        return response.data;
    } catch (error) {
        console.error('토큰 교환 실패:', error.message);
        return null;
    }
};

/**
 * 디스코드 사용자 프로필 조회
 * @param {string} token - 액세스 토큰
 * @returns {object|null} 사용자 프로필 또는 실패 시 null
 */
exports.getUserProfile = async (token) => {
    try {
        let response;
        let retryCount = 0;
        const maxRetries = 3;
        
        const authHeader = token.startsWith('Bearer ') ? token : `Bearer ${token}`;
        
        while (retryCount < maxRetries) {
            try {
                response = await axios.get('https://discord.com/api/v10/users/@me', {
                    headers: {
                        'Authorization': authHeader
                    },
                    timeout: 10000
                });
                return response.data;
            } catch (requestError) {
                if (requestError.response) {
                    if (requestError.response.status === 401) {
                        return null;
                    } else if (requestError.response.status === 429) {
                        const retryAfter = requestError.response.data.retry_after || 5;
                        await new Promise(resolve => setTimeout(resolve, (retryAfter + 1) * 1000));
                    }
                }
                
                retryCount++;
                if (retryCount >= maxRetries) {
                    return null;
                }
            }
        }
        
        return null;
    } catch (error) {
        console.error('사용자 프로필 정보 가져오기 실패:', error.message);
        return null;
    }
};

/**
 * 디스코드 웹훅으로 메시지 전송
 * @param {string} webhookUrl - 디스코드 웹훅 URL
 * @param {object} message - 전송할 메시지 객체
 * @returns {boolean} 전송 성공 여부
 */
exports.sendWebhookMessage = async (webhookUrl, message) => {
    try {
        const response = await axios.post(webhookUrl, message);
        return response.status === 204;
    } catch (error) {
        console.error('디스코드 웹훅 전송 실패:', error);
        return false;
    }
};

/**
 * 디스코드 임베드 생성
 * @param {object} options - 임베드 옵션
 * @returns {object} 디스코드 임베드 객체
 */
exports.createEmbed = (options) => {
    const { title, description, color, fields, timestamp, footer, thumbnail } = options;
    
    const embed = {
        title: title || '',
        description: description || '',
        color: color || 0x0099ff,
        fields: fields || [],
        timestamp: timestamp ? new Date().toISOString() : null
    };
    
    if (footer) {
        embed.footer = footer;
    }
    
    if (thumbnail) {
        embed.thumbnail = { url: thumbnail };
    }
    
    return embed;
};

/**
 * 경고 임베드 생성
 * @param {string} title - 임베드 제목
 * @param {string} description - 임베드 설명
 * @returns {object} 경고 임베드 객체
 */
exports.createWarningEmbed = (title, description) => {
    return exports.createEmbed({
        title: title || '⚠️ 경고',
        description: description,
        color: 0xffcc00
    });
};

/**
 * 오류 임베드 생성
 * @param {string} title - 임베드 제목
 * @param {string} description - 임베드 설명
 * @returns {object} 오류 임베드 객체
 */
exports.createErrorEmbed = (title, description) => {
    return exports.createEmbed({
        title: title || '❌ 오류',
        description: description,
        color: 0xff0000
    });
};

/**
 * 성공 임베드 생성
 * @param {string} title - 임베드 제목
 * @param {string} description - 임베드 설명
 * @returns {object} 성공 임베드 객체
 */
exports.createSuccessEmbed = (title, description) => {
    return exports.createEmbed({
        title: title || '✅ 성공',
        description: description,
        color: 0x00ff00
    });
}; 