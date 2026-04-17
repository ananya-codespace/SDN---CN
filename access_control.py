# access_control.py
# ---------------------------------------------------------------------------
# SDN-Based Access Control Whitelist Implementation for POX
# Purpose: Block unauthorized MAC addresses (h3, h4) and allow h1, h2.
# ---------------------------------------------------------------------------

from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.addresses import EthAddr

# Set up a logger to display messages in the terminal
log = core.getLogger()

# --- CONFIGURATION: THE SECURITY WHITELIST ---
# We define which devices are allowed on our network.
# h1 = ...:01, h2 = ...:02. Devices h3 and h4 are NOT here, so they get blocked.
WHITELIST = [
    '00:00:00:00:00:01', 
    '00:00:00:00:00:02'
]

class AccessControl (object):
  def __init__ (self, connection):
    # Store the connection link to the switch
    self.connection = connection
    
    # Register this class to listen for events (like packets arriving)
    connection.addListeners(self)

    # Initialize a MAC-to-Port table for learning switch behavior
    # This helps the switch remember which wire leads to which host.
    self.mac_to_port = {}

  def _handle_PacketIn (self, event):
    """
    This function runs every time a packet arrives at the switch 
    without a matching rule in the flow table.
    """
    packet = event.parsed # Parse the incoming packet data
    if not packet.parsed:
      return

    # Convert the source, destination, and input port to strings/integers
    src_mac = str(packet.src)
    dst_mac = str(packet.dst)
    in_port = event.port

    # --- STEP 1: SECURITY GATE (WHITELIST CHECK) ---
    # Check if the sender's MAC address is in our allowed list.
    if src_mac not in WHITELIST:
      # If not in whitelist, log the denial and exit (drops the packet)
      log.info("ACCESS DENIED: Unauthorized packet from %s dropped", src_mac)
      return

    # If code reaches here, the device is authorized.
    log.info("ACCESS GRANTED: Authorized packet from %s", src_mac)

    # --- STEP 2: ADDRESS LEARNING ---
    # The controller learns that src_mac is reachable via the port it just arrived on.
    self.mac_to_port[src_mac] = in_port

    # --- STEP 3: FLOW RULE INSTALLATION (MATCH-ACTION) ---
    # If the destination MAC is already in our learned table:
    if dst_mac in self.mac_to_port:
      out_port = self.mac_to_port[dst_mac]
      
      log.info("INSTALLING FLOW: %s -> %s on Port %d", src_mac, dst_mac, out_port)
      
      # Create a Flow Modification message to update the switch's hardware table
      msg = of.ofp_flow_mod()
      
      # Match: The rule applies to any future packet with these specific headers
      msg.match = of.ofp_match.from_packet(packet, in_port)
      
      # Timeout: The rule is deleted if no traffic is seen for 30 seconds
      msg.idle_timeout = 30
      
      # Action: Send the packet out of the learned destination port
      msg.actions.append(of.ofp_action_output(port = out_port))
      
      # Send the rule to the switch so it handles future packets itself
      self.connection.send(msg)
      
      # Also forward this current first packet out so it isn't lost
      msg_out = of.ofp_packet_out()
      msg_out.data = event.ofp
      msg_out.actions.append(of.ofp_action_output(port = out_port))
      self.connection.send(msg_out)

    else:
      # If we don't know where the destination is, flood the packet to everyone (broadcast)
      msg = of.ofp_packet_out()
      msg.data = event.ofp
      msg.actions.append(of.ofp_action_output(port = of.OFPP_ALL))
      self.connection.send(msg)

def launch ():
  """
  The main entry point for POX.
  """
  def start_switch (event):
    log.info("Switch connected. Loading Access Control Policy...")
    # Initialize our controller class for the connected switch
    AccessControl(event.connection)

  # Start listening for switches connecting to our controller
  core.openflow.addListenerByName("ConnectionUp", start_switch)