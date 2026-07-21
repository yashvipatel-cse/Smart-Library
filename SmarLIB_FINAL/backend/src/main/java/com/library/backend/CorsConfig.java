package com.library.backend;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

/**
 * Global CORS configuration for the SmartLib Spring Boot backend.
 *
 * This fixes all "Access-Control-Allow-Origin" errors in the browser console.
 * Allows requests from:
 *   - http://localhost:5500   (Live Server / frontend dev)
 *   - http://127.0.0.1:5500
 *   - http://YOUR_PC_IP:5500  (phone access over WiFi)
 */
@Configuration
public class CorsConfig {

    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();

        // Allow all origins — for production, replace with your domain
        config.addAllowedOriginPattern("*");
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        config.setAllowCredentials(false);

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);

        return new CorsFilter(source);
    }
}
