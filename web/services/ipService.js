const axios = require('axios');

/**
 * IP 정보 조회
 * @param {string} ipAddress - IP 주소
 * @returns {object|null} IP 정보 객체 또는 null
 */
exports.getIpInfo = async (ipAddress) => {
    try {
        const response = await axios.get(`http://ipinfo.io/${ipAddress}/json`);
        if (response.status === 200) {
            const data = response.data;
            return {
                country: data.country || 'N/A',
                region: data.region || 'N/A',
                isp: data.org || 'N/A'
            };
        } else {
            return {
                country: 'N/A',
                region: 'N/A',
                isp: 'N/A'
            };
        }
    } catch (error) {
        console.error('IP 정보 조회 실패:', error);
        return {
            country: 'N/A',
            region: 'N/A',
            isp: 'N/A'
        };
    }
};

/**
 * VPN 사용 여부 확인
 * @param {string} ip - IP 주소
 * @param {object} config - 앱 설정
 * @returns {boolean} VPN 사용 여부
 */
exports.checkIsVpn = async (ip, config) => {
    try {
        if (!config.vpnApiKey || config.vpnApiKey === '') {
            return false;
        }
        const response = await axios.get(`https://vpnapi.io/api/${ip}?key=${config.vpnApiKey}`);
        
        if (response.data && response.data.security && typeof response.data.security.vpn === 'boolean') {
            return response.data.security.vpn;
        } else {
            return false;
        }
    } catch (error) {
        console.error('VPN 확인 실패:', error);
        return false;
    }
}; 

// V1.3