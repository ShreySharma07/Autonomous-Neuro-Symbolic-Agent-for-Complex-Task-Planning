from neo4j import GraphDatabase

class KitchenWorld:
    def __init__(self, uri ,user, password):
        self._driver = GraphDatabase.driver(uri, auth=(user,password))
    
    def close(self):
        self._driver.close()
    
    def _run_query(self, query, parameters=None):
        with self._driver.session() as session:
            result = session.run(query, parameters)
            return [record for record in result]
    
    # --- SENSORY ACTIONS (The Agent's Senses) ---

    def look_around(self):
        query = """
        //find agent and its location
        MATCH (agent:Agent {name: 'Chef'})-[:IS_IN]->(room:Room)
        MATCH (location:Location)-[:PART_OF]->(room)
        MATCH (object:Object)-[:IS_IN]->(location)
        RETURN object.name AS object_name, location.name as location_name
        """
        records = self._run_query(query)
        # object_names = [record["object_name"] for record in records]
        # return f"You are in the {self.get_agent_location()}. You see the following objects {', '.join(object_names)}"
        if not records:
            return "You don't see any object"
        
        locations = {}
        for record in records:
            loc = record['location_name']
            obj = record['object_name']
            if loc not in locations:
                locations[loc] = []
            locations[loc].append(obj)
        
        observation_part = [f'You are in the {self.get_agent_location()}']
        observation_part.append('You see the following')
        for loc, objs in locations.items():
            observation_part.append(f"- In the {loc}: {', '.join(objs)}")
        
        return '\n'.join(observation_part)
    
    def get_agent_location(self):
        query = """
            MATCH (agent: Agent {name: 'Chef'})-[IS_IN]->(location)
            RETURN location.name AS location_name
            """
        records = self._run_query(query)
        if records:
            return records[0]['location_name']
        else:
            return 'Unknown Location'
        
    def get_object_info(self, object_name):
        query = """
              MATCH (o: Object {name: $object_name})
              RETURN properties(o) AS object_properties
        """

        records = self._run_query(query, {'object_name': object_name})
        if records:
            return records[0]["object_properties"]
        return f"Object '{object_name}' not found"
    

if __name__=='__main__':
    world = KitchenWorld("neo4j://localhost:7687", 'neo4j', '***REDACTED***')

    print('---testing sensory functions---')

    #Testing looking around
    observation = world.look_around()
    print('look_around()')
    print(observation)
    print('-'*20)

    #testing getting info about a specific object
    stove_info = world.get_object_info('Stove')
    print(f'get_object_info(stove):')
    print(stove_info)
    print('-'*20)


    world.close()
    print('script finished, connection closed')