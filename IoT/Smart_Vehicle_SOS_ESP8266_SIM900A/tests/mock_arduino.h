#ifndef MOCK_ARDUINO_H
#define MOCK_ARDUINO_H

#include <iostream>
#include <string>
#include <cstring>
#include <vector>
#include <cstdint>

// Types
typedef uint8_t byte;

// F() macro mock
#define F(x) x
#define PROGMEM

// Print mock
class PrintMock {
public:
    void print(const char* s) { std::cout << s; }
    void println(const char* s) { std::cout << s << std::endl; }
    void println() { std::cout << std::endl; }
};

extern PrintMock Serial;

// EEPROM Mock
class EEPROMMock {
private:
    std::vector<uint8_t> data;
public:
    void begin(size_t size) {
        data.resize(size, 0xFF); // Uninitialized flash is typically 0xFF
    }
    
    template<typename T>
    T& get(int const address, T& t) {
        if (address + sizeof(T) <= data.size()) {
            std::memcpy(&t, &data[address], sizeof(T));
        }
        return t;
    }
    
    template<typename T>
    const T& put(int const address, const T& t) {
        if (address + sizeof(T) <= data.size()) {
            std::memcpy(&data[address], &t, sizeof(T));
        }
        return t;
    }
    
    bool commit() { return true; }
    
    // Test helper to wipe flash
    void wipe() {
        std::fill(data.begin(), data.end(), 0xFF);
    }
};

extern EEPROMMock EEPROM;

// Missing Arduino functions
inline bool isDigit(char c) {
    return c >= '0' && c <= '9';
}

#endif // MOCK_ARDUINO_H
