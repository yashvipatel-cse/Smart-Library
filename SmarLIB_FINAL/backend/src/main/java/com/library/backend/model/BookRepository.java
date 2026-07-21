package com.library.backend.model;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

/**
 * Spring Data JPA repository for the unified `books` table.
 *
 * - Camera Scan uses findByBookNumberIgnoreCase(code)
 * - RFID Scan   uses findByRfidUidIgnoreCase(uid)
 */
public interface BookRepository extends JpaRepository<Book, Long> {

    // Used by Camera Scan (OCR reads book label codes like B001)
    Optional<Book> findByBookNumberIgnoreCase(String bookNumber);

    // Used by RFID Scan (ESP32 scans NFC tag UIDs)
    Optional<Book> findByRfidUidIgnoreCase(String rfidUid);
}
