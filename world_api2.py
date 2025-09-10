from neo4j import GraphDatabase

class KitchenWorld:
    def __init__(self, uri, user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self._driver.close()

    def _run_query(self, query, parameters=None):
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]
    
#     def look_around(self):
#         query = """
#            MATCH (agent:Agent {name:'Chef'})-[:IS_IN]->(location)
#            OPTIONAL MATCH (location)<-[:PART_OF]-(room:Room)
#            WITH coalesce(room, location) AS agent_room
#            MATCH (loc:Location)-[:PART_OF]->(agent_room)
#            MATCH (obj:Object)-[:IS_IN]->(loc)
#            RETURN obj.name AS object_name, loc.name AS location_name
# """
#         records = self._run_query(query)
#         if not records:
#             return "You don't see any object"
        
#         locations = {}
#         for record in records:
#             loc = record['location_name']
#             obj = record['object_name']
#             if not loc in locations: locations[loc] = []
#             locations[loc].append(obj)
        
#         observation_parts = [f'you are in the {self.get_agent_location()}.']
#         observation_parts.append('You see the following')

#         for loc, objs in locations.items():
#             observation_parts.append(f'- In the {loc}: {', '.join(objs)}')
        
#         return "\n".join(observation_parts)
    
    def look_around(self):
        """Finds all objects in the same room as the agent."""
        # This simpler query finds the agent's location, then finds the room,
        # then finds everything in that room.
        query = """
        MATCH (agent:Agent {name: 'Chef'})-[:IS_IN]->(loc)
        MATCH (loc)-[:PART_OF*0..]->(room:Room)
        MATCH (obj_loc:Location)-[:PART_OF]->(room)
        MATCH (obj:Object)-[:IS_IN]->(obj_loc)
        RETURN obj.name AS object_name, obj_loc.name as location_name
        """
        records = self._run_query(query)
        if not records:
            agent_loc = self.get_agent_location()
            # If the agent is holding something, that's all it sees
            holding_records = self._run_query("MATCH (:Agent)-[:HOLDS]->(obj:Object) RETURN obj.name as object")
            if holding_records:
                return f"You are in the {agent_loc}. You are holding the {holding_records[0]['object']}."
            return f"You are in the {agent_loc}, but you don't see any objects."

        locations = {}
        for record in records:
            loc, obj = record["location_name"], record["object_name"]
            if loc not in locations: locations[loc] = []
            locations[loc].append(obj)

        observation_parts = [f"You are in the {self.get_agent_location()}."]
        observation_parts.append("You see the following:")
        for loc, objs in sorted(locations.items()):
            observation_parts.append(f"- In the {loc}: {', '.join(sorted(objs))}")

        return "\n".join(observation_parts)
    
    def get_agent_location(self):
        query = """
            MATCH (agent:Agent {name:'Chef'})-[:IS_IN]->(location)
            RETURN location.name AS location_name
            """
        records = self._run_query(query)
        return records[0]['location_name'] if records else 'Unknown Location'
    
    def get_object_info(self, object_name):
        query = """
            MATCH (o:Object {name: $object_name}) RETURN properties(o) AS object_properties
"""
        records = self._run_query(query, {'object_name': object_name})
        return records[0]['object_properties'] if records else f"object '{object_name}' not found"
    
    def go_to(self, location_name):
        """Moves the agent to a new location."""
        # First, check if the location exists to avoid errors
        location_exists = self._run_query(
            "MATCH (loc:Location {name: $location_name}) RETURN loc",
            {'location_name': location_name}
        )
        if not location_exists:
            return f"Error: Location '{location_name}' does not exist."

        # Delete the old IS_IN relationship
        self._run_query("""
            MATCH (agent:Agent {name: 'Chef'})-[rel:IS_IN]->()
            DELETE rel
        """)

        # Create the new IS_IN relationship with the specific :Location label
        self._run_query("""
            MATCH (agent:Agent {name: 'Chef'})
            MATCH (location:Location {name: $location_name})
            MERGE (agent)-[:IS_IN]->(location)
        """, {'location_name': location_name})

        return f"You moved to the {location_name}."
    
    def pickup(self, object_name):
        """Picks up an object from the agent's current location."""
        # 1. Check if agent is already holding something
        holding = self._run_query("MATCH (:Agent {name:'Chef'})-[r:HOLDS]->(:Object) RETURN r")

        if holding:
            return "You are already holding something. You must put it down first."
        
        records = self._run_query(
            """
            MATCH (agent:Agent {name:'Chef'})-[:IS_IN]->(loc)
            MATCH (obj:Object {name:$object_name})-[:IS_IN]->(loc)
            RETURN obj
        """, {'object_name': object_name}
        )

        if not records:
            return f"You don't see a {object_name} here"
        
        # If checks pass, perform the pickup action
        self._run_query("""
            MATCH (agent:Agent {name:'Chef'})
            MATCH (obj:Object {name:$object_name})
            MATCH (obj)-[r:IS_IN]->()
            DELETE r
            MERGE (agent)-[:HOLDS]->(obj)
        """, {'object_name': object_name})
        return f"You picked up the {object_name}."
    
    def put_down(self, location_name):
        """Puts down the currently held object into a specified location."""
        # 1. Check what object the agent is holding
        records = self._run_query("""
            MATCH (agent:Agent {name:'Chef'})-[r:HOLDS]->(obj:Object)
            RETURN obj.name as held_object
        """)
        if not records:
            return "You are not holding anything."
        
        held_object = records[0]["held_object"]

        # 2. Perform the put down action
        self._run_query("""
            MATCH (agent:Agent {name:'Chef'})-[r:HOLDS]->(obj:Object)
            MATCH (loc:Location {name:$location_name})
            DELETE r
            MERGE (obj)-[:IS_IN]->(loc)
        """, {'location_name': location_name})
        return f"You put down the {held_object} in the {location_name}."
    
    def get_inventory(self):
        records = self._run_query("MATCH (:Agent)-[:HOLDS]->(obj:Object) RETURN obj.name as object")
        if records:
            return f"You are holding the {records[0]['object']}."
        return "You are holding nothing."
    


if __name__ == "__main__":
    world = KitchenWorld("neo4j://localhost:7687", 'neo4j', '***REDACTED***')

    print("--- Testing Action Functions ---")
    print(f"Initial location: {world.get_agent_location()}")

    # Simulate a sequence of actions
    print("\n1. Going to the Drawer...")
    print(world.go_to("Drawer"))
    print(f"Current location: {world.get_agent_location()}")

    print("\n2. Picking up the Knife...")
    print(world.pickup("Knife"))
    
    print("\n3. Trying to pick up another object (should fail)...")
    print(world.pickup("Plate")) # This should fail gracefully

    print("\n4. Going to the Counter...")
    print(world.go_to("Counter"))

    print("\n5. Putting down the Knife...")
    print(world.put_down("Counter"))

    print("\n6. Final check with look_around...")
    print(world.look_around())

    world.close()
    print("\nScript finished. Connection closed.")    