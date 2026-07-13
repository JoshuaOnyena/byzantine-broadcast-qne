from netqasm.sdk import EPRSocket
from netqasm.sdk.external import NetQASMConnection, Socket
from netqasm.logging.output import get_new_app_logger

KEY_LEN = 3
DEFAULT = 0


def main(app_config=None):
    logger = get_new_app_logger(app_name=app_config.app_name,
                                log_config=app_config.log_config)

    epr_gen = EPRSocket("general")
    epr_l2 = EPRSocket("lieutenant2")
    c_gen = Socket("lieutenant1", "general", log_config=app_config.log_config, socket_id=1)
    c_l2 = Socket("lieutenant1", "lieutenant2", log_config=app_config.log_config, socket_id=2)

    conn = NetQASMConnection(app_name=app_config.app_name,
                             log_config=app_config.log_config,
                             epr_sockets=[epr_gen, epr_l2],
                             max_qubits=1)

    k_gen, k_l2 = [], []
    with conn:
        # responder to general (matches general creating L1 pairs first)
        for _ in range(KEY_LEN):
            q = epr_gen.recv_keep()[0]
            m = q.measure()
            conn.flush()
            k_gen.append(int(m))
        # initiator to L2
        for _ in range(KEY_LEN):
            q = epr_l2.create_keep()[0]
            m = q.measure()
            conn.flush()
            k_l2.append(int(m))

    raw = c_gen.recv()
    order_str, tag_str = raw.split("|")
    my_order = int(order_str)
    recv_tag = [int(x) for x in tag_str.split(",")]
    order_authentic = (recv_tag == [k_gen[0] ^ my_order, k_gen[1], k_gen[2]])

    c_l2.send(f"{my_order}|{','.join(map(str, k_l2))}")
    peer_raw = c_l2.recv()
    peer_order_str, peer_key_str = peer_raw.split("|")
    peer_order = int(peer_order_str)
    peer_key = [int(x) for x in peer_key_str.split(",")]
    peer_authentic = (peer_key == k_l2)

    if not order_authentic or not peer_authentic:
        decision, note = DEFAULT, "authentication failure -> default"
    elif my_order == peer_order:
        decision, note = my_order, "orders consistent"
    else:
        decision, note = DEFAULT, "TRAITOR DETECTED (order mismatch) -> default"

    logger.log(f"L1 my_order={my_order} peer_order={peer_order} decision={decision} ({note})")
    return {"my_order": my_order, "peer_order": peer_order, "decision": decision, "note": note}
