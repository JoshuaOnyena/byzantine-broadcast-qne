from netqasm.sdk import EPRSocket
from netqasm.sdk.external import NetQASMConnection, Socket
from netqasm.logging.output import get_new_app_logger

KEY_LEN = 3


def _tag(key, order_bit):
    return [key[0] ^ order_bit, key[1], key[2]]


def main(app_config=None, order=1, faulty=0):
    logger = get_new_app_logger(app_name=app_config.app_name,
                                log_config=app_config.log_config)

    epr_l1 = EPRSocket("lieutenant1")
    epr_l2 = EPRSocket("lieutenant2")
    c_l1 = Socket("general", "lieutenant1", log_config=app_config.log_config, socket_id=1)
    c_l2 = Socket("general", "lieutenant2", log_config=app_config.log_config, socket_id=1)

    conn = NetQASMConnection(app_name=app_config.app_name,
                             log_config=app_config.log_config,
                             epr_sockets=[epr_l1, epr_l2],
                             max_qubits=1)

    k1, k2 = [], []
    with conn:
        for _ in range(KEY_LEN):
            q = epr_l1.create_keep()[0]
            m = q.measure()
            conn.flush()
            k1.append(int(m))
        for _ in range(KEY_LEN):
            q = epr_l2.create_keep()[0]
            m = q.measure()
            conn.flush()
            k2.append(int(m))

    order = int(order)
    order_to_l1 = order
    order_to_l2 = (1 - order) if int(faulty) else order

    c_l1.send(f"{order_to_l1}|{','.join(map(str, _tag(k1, order_to_l1)))}")
    c_l2.send(f"{order_to_l2}|{','.join(map(str, _tag(k2, order_to_l2)))}")

    logger.log(f"general faulty={bool(int(faulty))} sent L1={order_to_l1} L2={order_to_l2}")
    return {"faulty": int(faulty), "order_to_l1": order_to_l1, "order_to_l2": order_to_l2}
