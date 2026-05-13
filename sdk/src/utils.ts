export const logger = {
    info: (msg: string): void => console.log(`[Analytics-SDK] Info: ${Date.now().toString()} ${msg}`),
    error: (msg: string): void => console.error(`[Analytics-SDK] Error: ${Date.now().toString()} ${msg}`),
    warn: (msg: string): void => console.warn(`[Analytics-SDK] Warning: ${Date.now().toString()} ${msg}`),
};