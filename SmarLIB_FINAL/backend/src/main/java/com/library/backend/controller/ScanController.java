package com.library.backend.controller;

import org.springframework.web.bind.annotation.*;

/**
 * ScanController — health check endpoint only.
 * GET /api/test → returns "ok" (used by frontend to check if Java is alive)
 */
@RestController
@CrossOrigin(origins = "*", allowedHeaders = "*")
@RequestMapping("/api")
public class ScanController {

    /** Health-check — called by frontend every 15s */
    @GetMapping("/test")
    public String test() {
        return "ok";
    }
}
/*
 * GLOBAL CORS FIX — add this bean to BackendApplication.java if CORS errors persist:
 *
 * import org.springframework.context.annotation.Bean;
 * import org.springframework.web.cors.*;
 * import org.springframework.web.filter.CorsFilter;
 *
 * @Bean
 * public CorsFilter corsFilter() {
 *     CorsConfiguration cfg = new CorsConfiguration();
 *     cfg.addAllowedOriginPattern("*");
 *     cfg.addAllowedMethod("*");
 *     cfg.addAllowedHeader("*");
 *     UrlBasedCorsConfigurationSource src = new UrlBasedCorsConfigurationSource();
 *     src.registerCorsConfiguration("/**", cfg);
 *     return new CorsFilter(src);
 * }
 */
