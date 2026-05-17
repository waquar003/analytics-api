interface BrowserMetadata {
    screen_width: number;
    screen_height: number;
    language: string;
    languages: readonly string[];
    userAgent: string;
    referrer: string;
}

interface EventContext {
    url: string;
    session_id: string;
    user_id: string;
    metadata: BrowserMetadata;
}

const getSessionId = (): string => {
    let sessionId = sessionStorage.getItem('analytics_session_id');
    if (!sessionId) {
        sessionId = crypto.randomUUID();
        sessionStorage.setItem('analytics_session_id', sessionId);
    }
    return sessionId;
}

const getUserId = (): string => {
    let userId = localStorage.getItem('analytics_user_id');
    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem('analytics_user_id', userId);
    }

    return userId
}

const getBrowserMetadata = (): BrowserMetadata => {
    return {
        screen_width: window.screen.width,
        screen_height: window.screen.height,
        language: navigator.language,
        languages: navigator.languages,
        userAgent: navigator.userAgent,
        referrer: document.referrer || 'direct',
    }
}

export const getEventContext = (): EventContext =>  {
    return {
        url: window.location.href,
        session_id: getSessionId(),
        user_id: getUserId(),
        metadata: getBrowserMetadata(),
    }
}