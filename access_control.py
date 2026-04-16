# access_control.py
# Implementation of an SDN-based Access Control Whitelist using POX
# For Orange Problem #11 - SDN Mininet Simulation

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import EthAddr

log = core.getLogger()

# --- CONFIGURATION: WHITELIST ---
# Only these MAC addresses are allowed to communicate.
# In default Mininet, h1 is 01, h2 is 02. h3 and h4 will be blocked.
WHITELIST = [
    '00:00:00:00:00:01',
    '00:00:00:00:00:02'
]

class AccessControl (object):
  def __init__ (self, connection):
    # Keep track of the connection to the switch
    self.connection = connection

    # This binds our PacketIn handler
    connection.addListeners(self)

    # Table to learn MAC addresses and ports (Learning Switch logic)
    self.mac_to_port = {}

  def _handle_PacketIn (self, event):
    """
    Handles packet_in messages from the switch.
    Implements Whitelisting and Match+Action logic.
    """
    packet = event.parsed # This is the parsed packet data
    if not packet.parsed:
      log.warning("Ignoring incomplete packet")
      return

    src_mac = str(packet.src)
    dst_mac = str(packet.dst)
    in_port = event.port

    # 1. SECURITY CHECK: Check if the source MAC is in the whitelist
    if src_mac not in WHITELIST:
      log.info("SECURITY ALERT: Dropped unauthorized packet from %s", src_mac)
      # We return without sending a response, which drops the packet
      return

    log.info("AUTHORIZED: Packet from %s seen on port %d", src_mac, in_port)

    # 2. LEARNING LOGIC: Map the source MAC to the port it arrived on
    self.mac_to_port[src_mac] = in_port

    # 3. FORWARDING / FLOW RULE LOGIC (Match + Action)
    # If we know where the destination is, install a flow rule
    if dst_mac in self.mac_to_port:
      out_port = self.mac_to_port[dst_mac]

      log.info("INSTALLING RULE: %s -> %s (Port %d)", src_mac, dst_mac, out_port)

      # Create an OpenFlow Flow Modification message
      msg = of.ofp_flow_mod()

      # Match: Based on source MAC, dest MAC, and input port
      msg.match = of.ofp_match.from_packet(packet, in_port)

      # Set Timeouts (rules disappear after 30s of inactivity)
      msg.idle_timeout = 30

      # Action: Output to the correct port
      msg.actions.append(of.ofp_action_output(port = out_port))

      # Send the rule to the switch
      self.connection.send(msg)

      # Also send the current packet out immediately
      msg_out = of.ofp_packet_out()
      msg_out.data = event.ofp
      msg_out.actions.append(of.ofp_action_output(port = out_port))
      self.connection.send(msg_out)

    else:
      # If destination is unknown, flood the packet to all ports
      log.debug("Unknown destination %s, flooding...", dst_mac)
      msg = of.ofp_packet_out()
      msg.data = event.ofp
      msg.actions.append(of.ofp_action_output(port = of.OFPP_ALL))
      self.connection.send(msg)

def launch ():
  """
  Starts the component when POX is run
  """
  def start_switch (event):
    log.info("Switch %s connected. Applying Access Control logic.", event.dpid)
    AccessControl(event.connection)

  # Listen for Switch connections
  core.openflow.addListenerByName("ConnectionUp", start_switch)