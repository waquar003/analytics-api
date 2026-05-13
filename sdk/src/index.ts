import config from "./config";
import { getEventContext } from "./context";
import { sendEvent } from "./transport";
import { logger } from "./utils";

class AnalyticsSDK {
    public init(publicKey: string, options: { baseUrl?: string; debug?: boolean }): void {
        if (config.initialized) {
            logger.warn('SDK is already initialized')
            return;
        }

        if (!publicKey || !publicKey.startsWith('pub_')) {
            logger.error('Invalid Public API Key. It must start with "pub_".');
            return;
        }

        config.publicKey = publicKey;
        config.baseUrl = options.baseUrl || config.baseUrl;
        config.debug = options.debug || false;
        config.initialized = true;

        if (config.debug) logger.info('SDK initialized successfully.');
    }

    public track(eventType: string = 'pageview', properties: Record<string, any> = {}): void {
        if (!config.initialized) {
            logger.error('Cannot track event. SDK not initialized');
            return;
        }

        const context = getEventContext();

        const payload = {
            event_type: eventType,
            url: context.url,
            session_id: context.session_id,
            user_id: context.user_id,
            properties: {
                ...context.metadata,
                ...properties,
            }
        }

        sendEvent(payload)
    }
}

const Analytics = new AnalyticsSDK();
if (typeof window !== 'undefined') {
    (window as any).Analytics = Analytics;
}
export default Analytics;