/*
Query to return ingress packet flow counts for a given interface that provides named IP addresses and subnets.
You can repeat the WHEN THEN statements to add other named IP addresses and subnets.

The query also adds the 'initiator' column to work out if the interface is likely acting as the client or server
in the captured flow. This is simply done by comparing the srcport to dstport. Where the srcport > dstport the flow
is labelled as server. Where srcport < dstport the flow is labelled as client. This isn’t exact, but works in most cases.

Replace the following values in the query:
------------------------------------------
<IP_ADDR_1> - IP address to name should be in x.x.x.x format (e.g. 10.1.1.1)
<NAMED_SOURCE> - The name label for IP_ADDR_1
<IP_SUBNET_1> - Subnet to name, should be in CIDR notation (e.g. 10.0.0.0/24)
<NAMED_SUBNET> - The name label for IP_SUBNET_1
<DATA_SOURCE>.<DATABASE>.<TABLE> - The datasource, database, and table to query against
<MONTH> - Month to query in, in mm format (e.g. 06)
<YEAR> - Year to query in, in yyyy format (e.g. 2024)
<INTERFACE_ID> - The interface ID to return results for. Can remove to query for all results
<SEARCH_SUBNET> - Add this in CIDR notation to return results for specific subnets

*/
SELECT 
    COUNT("interface_id") as flow_count,
    interface_id,
    CASE
        WHEN protocol = 6
        THEN 'tcp'
        WHEN protocol = 17
        THEN 'udp'
        WHEN protocol = 1
        THEN 'icmp'
        ELSE 'other'
    END as protocol,
    flow_direction,
    CASE
	WHEN srcaddr = <IP_ADDR_1>
	THEN <NAMED_SOURCE>
    	WHEN contains(<IP_SUBNET_1>, cast(srcaddr as IPADDRESS))
    	THEN 'NAMED_SUBNET'
    	ELSE 'other'
    END as in_subnet,
    srcaddr,
    srcport,
    dstaddr,
    dstport,
    CASE
        WHEN srcport > dstport
        THEN 'server'
        ELSE 'client'
    END as initator
FROM 
    <DATA_SOURCE>.<DATABASE>.<TABLE> 
WHERE 
    dstport is not null
    and month=<MONTH> and year=<YEAR>
    and action='ACCEPT'
    and interface_id= <INTERFACE_ID>
    and flow_direction = 'ingress'
    /* uncomment the next line to only return data for a specific subnet */
    --and contains(<SEARCH_SUBNET>, cast(srcaddr as IPADDRESS))
GROUP BY 
    interface_id,
    protocol,
    flow_direction,
    srcaddr,
    srcport,
    dstaddr,
    dstport
ORDER by flow_count desc
