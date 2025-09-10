from neo4j import GraphDatabase

uri = "neo4j://127.0.0.1:7687"
AUTH = ('neo4j', '***REDACTED***')

def clear_database(tx):
    tx.run("MATCH (n) DETACH DELETE n")
    print("database cleared")

def build_kitchen_world(tx):
    cypher_query = """
    MERGE (kitchen : Room {name : 'Kitchen'})

    //creating locations within the kitchen
    MERGE (counter:Location {name:'Counter'})-[:PART_OF]->(kitchen)
    MERGE (fridge:Location {name:'Fridge'})-[:PART_OF]->(kitchen)
    MERGE (cupboard:Location {name:'Cupboard'})-[:PART_OF]->(kitchen)
    MERGE (drawer:Location {name:'Drawer'})-[:PART_OF]->(kitchen)
    MERGE (stove_top:Location {name:'Stove_top'})-[:PART_OF]->(kitchen)

    //creating objects and their initial states and location
    MERGE (bread1:Object {name: 'Bread_Slice', id: 1, is_buttered:false})-[:IS_IN]->(cupboard)
    MERGE (bread2:Object {name: 'Bread_Slice', id: 2, is_buttered:false})-[:IS_IN]->(cupboard)
    MERGE (cheese_slice:Object {name: 'Cheese_Slice'})-[:IS_IN]->(fridge)
    MERGE (butter:Object {name: 'Butter'})-[:IS_IN]->(fridge)
    MERGE (knife:Object {name: 'Knife'})-[:IS_IN]->(drawer)
    MERGE (plate:Object {name: 'Plate'})-[:IS_IN]->(cupboard)
    MERGE (pan:Object {name: 'Pan'})-[:IS_IN]->(cupboard)
    MERGE (stove:Object {name: 'Stove', is_on:false})-[:IS_IN]->(stove_top)

    //creating agent and its initial location
    MERGE (agent:Agent {name: 'Chef'})-[:IS_IN]->(kitchen)
"""
    tx.run(cypher_query)
    print('kitchen world created successfully')

if __name__=='__main__':
    try:
        with GraphDatabase.driver(uri, auth=AUTH) as driver:
            with driver.session() as session:
                session.execute_write(clear_database)
                session.execute_write(build_kitchen_world)
                print('script finished')
    except Exception as e:
        print(f'An error occured {e}')