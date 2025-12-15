#ifndef THREE_PHASE_CURRENT_PACKET_H
#define THREE_PHASE_CURRENT_PACKET_H

/**
 * @brief Packet containing three-phase current measurements (amps).
 */
struct ThreePhaseCurrentPacket {
    float ia;
    float ib;
    float ic;
};

#endif