from django.shortcuts import render

from django.http import HttpResponse, Http404
import pyodbc
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.http import FileResponse, JsonResponse
from django.forms.models import model_to_dict
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User
from .serializers import RegisterSerializer, LoginSerializer
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import MyappDepnp,MyappEmpyp,MyappElghp,NotesEntry,AlternativeAddressTable,MyappTermedMembers
from .claims import fetch_claims_data_for_clmp,fetch_claims_data_for_member_using_ssn,fetch_claims_data_using_claim_no,get_claims_count,generate_claim_report,get_class_name,get_plan_name,check_COB,fetch_claims_data_for_dependent_using_ssn
from rest_framework.decorators import api_view
import json
from io import BytesIO
import pyodbc
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.db.utils import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
import shutil, os, re
from datetime import datetime
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from .serializers import MyappTermedMemberSerializer,NotesEntrySerializer,MyappRecentDataSerializer,AlternativeAddressTableSerializer,SignupSerializer,EmployeeSerializer, LoginSerializer,OTPLoginSerializer,CountSerializer,EmpypSerializer,DepnpSerializer,CustodialSerializer
import pandas as pd
import tempfile
from django.core.files.storage import FileSystemStorage
import mimetypes
from django.conf import settings
from django.utils.encoding import smart_str
from django.utils.timezone import timedelta
from django.utils.timezone import now
from .models import MyappEmpyp,MyappDepnp,MyappElghp,MyappMssqlCountModel,MyappRecentData,MyappMemberCount,MyappCustodialDataTable


        

from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import MyappEmpyp
from .serializers import EmployeeSerializer
from django.forms.models import model_to_dict


schema_name = "ooedf"

host = '104.153.122.227'
port = '23'
database = 'S78F13CW'
user = 'ONEPYTHON'
password = 'pa33word'

connection_string = (
    f"DRIVER={{iSeries Access ODBC Driver}};"
    f"SYSTEM={host};"
    f"PORT={port};"
    f"DATABASE={database};"
    f"UID={user};"
    f"PWD={password};"
    f"PROTOCOL=TCPIP;"
)


class RegisterAPIView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save()
                return Response({"message": "User registered successfully!"}, status=status.HTTP_201_CREATED)
            except IntegrityError as e:
                if 'UQ_Users_Email' in str(e):  # Check for unique constraint violation
                    return Response({"message": "Email already exists. Please use a different email."}, status=status.HTTP_400_BAD_REQUEST)
                return Response({"message": "An error occurred while saving the user."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            try:
                user = User.objects.get(email=email, password=password)  
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)

                return Response({
                    "message": f"Welcome {user.name}!",
                    "access_token": access_token,
                    "ssn": user.ssn,
                    "is_admin":True
                }, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                return Response({"message": "Invalid email or password"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class Get_Count(APIView):
    def post(self,request):
        data = request.data
        date = data.get('date')
        try:
            db_data = MyappMssqlCountModel.objects.get(date=date)
        except:
            return Response("No data found")
        db_data_dict = model_to_dict(db_data)
        print(db_data_dict)
        return Response({"data": db_data_dict}, status=200)
    
class GET_CLAIMS_COUNT(APIView):
    def get(self,request):
        date_str = request.GET.get('date')
        claim_count = get_claims_count(date_str)
        return Response({"claim_count":claim_count,"date":date_str})


@api_view(['GET'])
def search_members(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({"error": "Search query is required"}, status=400)

    sanitized_query = query.replace("-", "")

    mssql_conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=ABCCOLUMBUSSQL2;'
        'DATABASE=EDIDATABASE;'
        'UID=sa;'
        'PWD=ChangeMe#2024;'
    )
    
    sql_query = """
        SELECT TOP 50 * 
        FROM myapp_empyp
        WHERE 
            emname LIKE ? OR
            REPLACE(emssn, '-', '') LIKE ? OR
            emmem LIKE ?
        ORDER BY emname
    """

    search_param = f"%{sanitized_query}%"
    
    with mssql_conn.cursor() as cursor:
        cursor.execute(sql_query, (search_param, search_param, search_param))
        columns = [col[0].lower() for col in cursor.description]  
        rows = cursor.fetchall()

    results = [dict(zip(columns, row)) for row in rows]

    mssql_conn.close()

    return JsonResponse({"results": results})

@api_view(['GET'])
def serach_members_db2(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({"error": "Search query is required"}, status=400)

    sanitized_query = query.replace("-", "")
    connection = pyodbc.connect(connection_string)

    sql_query = f"""
        SELECT 
            e.*, 
            g.ELCLAS, 
            g.ELPLAN
        FROM {schema_name}.empyp e
        LEFT JOIN {schema_name}.elghp g ON e.EMSSN = g.ELSSN
        WHERE 
            e.EMNAME LIKE ? OR
            REPLACE(e.EMSSN, '-', '') LIKE ? OR
            e.EMMEM# LIKE ?
        ORDER BY e.EMNAME
        FETCH FIRST 15 ROWS ONLY
    """


    search_param = f"%{sanitized_query}%"

    with connection.cursor() as cursor:
        cursor.execute(sql_query, (search_param, search_param, search_param))
        columns = [col[0].lower() for col in cursor.description]  
        rows = cursor.fetchall()

    results = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        if 'emname' in row_dict and row_dict['emname']:
            row_dict['emname'] = row_dict['emname'].replace("*", " ")
        results.append(row_dict)
    ssn_df = pd.DataFrame(results)
    ssn_df.drop_duplicates(subset=['emssn'],inplace=True)
    results = ssn_df.to_dict(orient='records')
    connection.close()

    return JsonResponse({"results": results})

@api_view(['GET'])
def serach_for_eligibility(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({"error": "Search query is required"}, status=400)

    sanitized_query = query.replace("-", "")
    connection = pyodbc.connect(connection_string)
    query_depnp = f"""
        SELECT 
            d.*
        FROM {schema_name}.depnp d
        WHERE 
            d.DPNAME LIKE ? OR
            REPLACE(d.DPDSSN, '-', '') LIKE ?
        ORDER BY d.DPNAME
        FETCH FIRST 50 ROWS ONLY """
    search_param = f"%{sanitized_query}%"

    with connection.cursor() as cursor:
        cursor.execute(query_depnp, (search_param, search_param))
        depnp_results = cursor.fetchall()
    depnp_data = [dict(zip([column[0].lower() for column in cursor.description], row)) for row in depnp_results]

    query_empyp = f"""
        SELECT 
            e.*, 
            g.ELCLAS, 
            g.ELPLAN,
            d.* 
        FROM {schema_name}.empyp e
        LEFT JOIN {schema_name}.elghp g ON e.EMSSN = g.ELSSN
        LEFT JOIN {schema_name}.depnp d ON e.EMSSN = d.DPSSN
        WHERE 
            e.EMNAME LIKE ? OR
            REPLACE(e.EMSSN, '-', '') LIKE ? OR
            e.EMMEM# LIKE ?
        ORDER BY e.EMNAME
        FETCH FIRST 50 ROWS ONLY
    """
    with connection.cursor() as cursor:
        cursor.execute(query_empyp, (search_param, search_param, search_param))
        empyp_results = cursor.fetchall()
    empyp_data = [dict(zip([column[0].lower() for column in cursor.description], row)) for row in empyp_results]
    merged_data = {
        "depnp_results": depnp_data,
        "empyp_results": empyp_data
    }
    return Response(merged_data)

class GetMemberCountView(APIView):
    def get(self, request):
        file_date = request.GET.get("file_date")

        if not file_date:
            return Response({"error": "file_date is required"}, status=status.HTTP_400_BAD_REQUEST)

    
        record = MyappMemberCount.objects.filter(file_date=file_date).first()

        if not record:
            return Response({"message": "No data found for the given date"}, status=status.HTTP_404_NOT_FOUND)

        response_data = {
            "new_members": record.new_members,
            "dropped_members": record.dropped_members,
            "file_date": record.file_date
        }

        return Response(response_data, status=status.HTTP_200_OK)


class GetClaimsDataView(APIView):
    def get(self, request):
        
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        ssn = request.query_params.get("ssn",None)
        dep_ssn = request.query_params.get("dep_ssn",None)
        mem_ssn = request.query_params.get("mem_ssn",None)

        if dep_ssn:
            dp_query = f"""SELECT DPSEQ FROM {schema_name}.depnp WHERE DPDSSN=?"""
            cursor.execute(dp_query, (dep_ssn))
            row = cursor.fetchone()
            dpseq = row[0]

        if ssn:
            ssn = str(ssn).replace("-", "")
            try:
                ssn_int = int(ssn)
            except ValueError:
                return Response({"error": "Invalid SSN format"}, status=status.HTTP_400_BAD_REQUEST)
            df = fetch_claims_data_for_member_using_ssn(ssn_int)
        elif mem_ssn:
            mem_ssn = str(mem_ssn).replace("-", "")
            try:
                dep_ssn_int = int(mem_ssn)
            except ValueError:
                return Response({"error": "Invalid SSN format"}, status=status.HTTP_400_BAD_REQUEST)
            df = fetch_claims_data_for_dependent_using_ssn(dep_ssn_int,dpseq)
        try:
            data_dict = df.to_dict(orient="records")
        except:
            data_dict = []
        return Response({"data": data_dict}, status=status.HTTP_200_OK)
    
class DownloadClaimsReport(APIView):
    def get(self, request):
        ssn = request.query_params.get("ssn")
        from_date = request.query_params.get("from_date")
        to_date = request.query_params.get("to_date")
        claims_no = request.query_params.get('claim_no',None)
        # to_m, to_d, to_y = to_date.split("/")
        # from_m, from_d, from_y =from_date.split("/")
        if not ssn:
            return Response({"error": "SSN is required"}, status=status.HTTP_400_BAD_REQUEST)
        ssn = str(ssn).replace("-", "")
        try:
            ssn_int = int(ssn)
        except ValueError:
            return Response({"error": "Invalid SSN format"}, status=status.HTTP_400_BAD_REQUEST)

        df = generate_claim_report(ssn_int,from_date,to_date,claims_no)
        try:
            df_dict  = df.to_dict(orient="records")
        except:
            df_dict = {}
        return Response(df_dict)
    



class GetClaimsDataUsingClaimNoView(APIView):
    def get(self, request):
        clm = request.query_params.get("claim_no")
        if not clm:
            return Response({"error": "CLM NO is required"}, status=status.HTTP_400_BAD_REQUEST)
        clm = str(clm)
        df = fetch_claims_data_using_claim_no(clm)
        data_dict = df.to_dict(orient="records")
        return Response({"data": data_dict}, status=status.HTTP_200_OK)
    
    
class GetTotalClaimsDataView(APIView):
    def get(self, request):
        df = fetch_claims_data_for_clmp()
        df['FOR'] = ''
        data_dict = df.to_dict(orient="records")
        return Response({"data": data_dict}, status=status.HTTP_200_OK)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pyodbc

class GetMemberAndDependentsViewDB2(APIView):
    def get(self, request):
        ssn = request.query_params.get("ssn")

        if not ssn:
            return Response({"error": "SSN is required"}, status=status.HTTP_400_BAD_REQUEST)

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        try:
            member_query = f"SELECT * FROM {schema_name}.empyp WHERE EMSSN = ?"
            cursor.execute(member_query, (ssn,))
            member_row = cursor.fetchone()

            if not member_row:
                return Response({"message": "No members found for the given SSN"}, status=status.HTTP_404_NOT_FOUND)

            member_columns = [desc[0].lower() for desc in cursor.description]
            member_data = dict(zip(member_columns, member_row))

            if 'emname' in member_data and member_data['emname']:
                member_data['emname'] = member_data['emname'].replace("*", " ")

            eligibility_query = f"""
                SELECT ELEPDY, ELEPDM, ELEPDD, ELPLAN, ELCLAS, ELHSTA
                FROM {schema_name}.elghp 
                WHERE ELSSN = ?
            """
            cursor.execute(eligibility_query, (ssn,))
            eligibility_row = cursor.fetchone()

            if eligibility_row:
                elepdy, elepdm, elepdd, elplan, elclas, elhsta = eligibility_row

                emeffect_date = f"{str(elepdm).zfill(2)}/{str(elepdd).zfill(2)}/{str(elepdy).zfill(4)}" if elepdy and elepdm and elepdd else None

                member_data["emeffdate"] = emeffect_date
                member_data["emplan"] = elplan
                member_data["emclas"] = elclas
                member_data["elhsta"] = elhsta

            dependents_query = f"SELECT * FROM {schema_name}.depnp WHERE DPSSN = ?"
            cursor.execute(dependents_query, (ssn,))
            dependents_rows = cursor.fetchall()
            dependent_columns = [desc[0].lower() for desc in cursor.description]
            dependent_data = [dict(zip(dependent_columns, row)) for row in dependents_rows]
            relationship_mapping = {
                "1": "spouse",
                "2": "son",
                "3": "daughter",
                "4": "stepchild",
                "9": "other"
            }
            for dep in dependent_data:
                if 'dpname' in dep and dep['dpname']:
                    dep['dpname'] = dep['dpname'].replace("*", " ")
                if 'dprltn' in dep:
                    dep['dptype'] = relationship_mapping.get(str(dep['dprltn']).strip(), "")

            custodial_query = f"SELECT * FROM {schema_name}.wbenp WHERE WBSSN = ?"
            cursor.execute(custodial_query, (ssn,))
            custodial_rows = cursor.fetchall()
            custodial_columns = [desc[0].lower() for desc in cursor.description]
            custodial_data = [dict(zip(custodial_columns, row)) for row in custodial_rows] if custodial_rows else []

            for cust in custodial_data:
                if 'wbname' in cust and cust['wbname']:
                    cust['wbname'] = cust['wbname'].replace("*", " ")

        finally:
            cursor.close()
            connection.close()

        return Response(
            {"member": member_data, "dependents": dependent_data, "custodial_data": custodial_data},
            status=status.HTTP_200_OK
        )


    
class GetMemberAndDependentsView(APIView):
    def get(self, request):
        ssn = request.query_params.get("ssn")

        if not ssn:
            return Response({"error": "SSN is required"}, status=status.HTTP_400_BAD_REQUEST)

        member = MyappEmpyp.objects.filter(emssn=ssn).order_by('-file_date').first()

        if not member:
            return Response({"message": "No members found for the given SSN"}, status=status.HTTP_404_NOT_FOUND)

        dependents = MyappDepnp.objects.filter(dpssn=member.emssn, file_date=member.file_date)
        custodial_dependents = MyappCustodialDataTable.objects.filter(ssn=member.emssn)
        member_data = EmpypSerializer(member).data
        dependent_data = DepnpSerializer(dependents, many=True).data
        if custodial_dependents:
            custodial_data = CustodialSerializer(custodial_dependents,many=True).data
        else:
            custodial_data = []

        return Response(
            {"member": member_data, "dependents": dependent_data,"custodial_data":custodial_data},
            status=status.HTTP_200_OK
        )


@api_view(['POST'])
def add_member(request):
    relationship = request.data.get("relationship")  
    if relationship != "Member":
        return Response({"error": "Only members can be added. Invalid relationship type."}, status=400)

    EMSSN = request.data.get("emssn")  
    if not EMSSN:
        return Response({"error": "SSN (emssn) is required."}, status=400)

    if MyappEmpyp.objects.filter(emssn=EMSSN).exists():
        return Response({"error": "SSN already exists. Duplicate entries are not allowed."}, status=400)

    try:
        EMNAME = request.data.get("emname")
        EMSEX = request.data.get("emsex")
        EMDOB = request.data.get("emdob")  
        EMADR1 = request.data.get("emadr1")
        EMCITY = request.data.get("emcity")
        EMST = request.data.get("emst")
        Country = request.data.get("country")  
        EMMEM = request.data.get("emmem")
        ELPLAN = request.data.get("elplan")
        ELCLAS = request.data.get("elclas")

        dob_parsed = None
        if EMDOB:
            try:
                dob_parsed = datetime.strptime(EMDOB, "%Y-%m-%d")
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        full_address = ", ".join(filter(None, [EMADR1, EMCITY, EMST, Country]))

        MyappEmpyp_obj = MyappEmpyp(
            emssn=EMSSN,
            emname=EMNAME,
            emsex=EMSEX,
            emdoby=dob_parsed.year if dob_parsed else None,
            emdobm=dob_parsed.month if dob_parsed else None,
            emdobd=dob_parsed.day if dob_parsed else None,
            emadr1=full_address,
            emcity=EMCITY,
            emst=EMST,
            emmem=EMMEM,
            emclas = ELCLAS,
            emplan = ELPLAN
        )
        MyappEmpyp_obj.save()


        return Response({"message": "Member added successfully!", "status": "success"})

    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
def add_member_db2(request):
    relationship = request.data.get("relationship")
    if relationship != "Member":
        return Response({"error": "Only members can be added."}, status=400)

    EMSSN = request.data.get("emssn")
    if not EMSSN:
        return Response({"error": "SSN (emssn) is required."}, status=400)

    try:
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        cursor.execute(f"SELECT COUNT(*) FROM {schema_name}.EMPYP WHERE EMSSN = ?", (EMSSN,))
        if cursor.fetchone()[0]:
            return Response({"error": "SSN already exists."}, status=400)

        EMNAME = request.data.get("emname")
        EMSEX = request.data.get("emsex")
        EMDOB = request.data.get("emdob")
        EMADR1 = request.data.get("emadr1")
        EMCITY = request.data.get("emcity")
        EMST = request.data.get("emst")
        Country = request.data.get("country")
        EMMEM = request.data.get("emmem")
        ELPLAN = request.data.get("elplan")
        ELCLAS = request.data.get("elclas")

        dob_parsed = None
        if EMDOB:
            try:
                dob_parsed = datetime.strptime(EMDOB, "%Y-%m-%d")
            except ValueError:
                return Response({"error": "Invalid date format."}, status=400)

        full_address = ", ".join(filter(None, [EMADR1, EMCITY, EMST, Country]))
        current_date = datetime.today()

        year = str(current_date.year)
        month = str(current_date.month)
        day = str(current_date.day)
        status = 'A'

        cursor.execute(f"""
            INSERT INTO {schema_name}.EMPYP (EMSSN, EMNAME, EMSEX, EMDOBY, EMDOBM, EMDOBD, EMADR1, EMCITY, EMST, EMMEM#)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) WITH NC
        """, (
            EMSSN,
            EMNAME,
            EMSEX,
            dob_parsed.year if dob_parsed else None,
            dob_parsed.month if dob_parsed else None,
            dob_parsed.day if dob_parsed else None,
            full_address,
            EMCITY,
            EMST,
            EMMEM
        ))

        cursor.execute(f"""
            INSERT INTO {schema_name}.ELGHP (ELSSN, ELCLAS, ELPLAN, ELHSTA, ELEPDY, ELEPDM, ELEPDD, ELUDTY, ELUDTM, ELUDTD)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) WITH NC
        """, (
            EMSSN,
            ELCLAS,
            ELPLAN,
            "A",
            year,
            month,
            day,
            year,
            month,
            day
        ))

        

        connection.commit()
        return Response({"message": "Member added successfully!"})

    except pyodbc.Error as e:
        return Response({"error": str(e)}, status=500)

    finally:
        cursor.close()
        connection.close()


@api_view(['POST'])
def add_dependents(request):
    relationship = request.data.get("relationship")  
    if relationship == "Member":
        return Response({"error": "Only Dependents can be added. Invalid relationship type."}, status=400)

    EMSSN = request.data.get("emssn")  
    DPDSSN = request.data.get("dpdssn")
    if not EMSSN:
        return Response({"error": "SSN (emssn) is required."}, status=400)

    if MyappDepnp.objects.filter(dpdssn=EMSSN).exists():
        return Response({"error": "SSN already exists. Duplicate entries are not allowed."}, status=400)

    try:
        EMNAME = request.data.get("dpname")
        EMSEX = request.data.get("dpsex")
        EMDOB = request.data.get("dpdob")  
        EMADR1 = request.data.get("dpadr1")
        EMCITY = request.data.get("dpcity")
        EMST = request.data.get("dpst")
        Country = request.data.get("country")  
        EMMEM = request.data.get("dpmem")
        ELPLAN = request.data.get("dpplan")
        ELCLAS = request.data.get("dpclas")

        dob_parsed = None
        if EMDOB:
            try:
                dob_parsed = datetime.strptime(EMDOB, "%Y-%m-%d")
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        full_address = ", ".join(filter(None, [EMADR1, EMCITY, EMST, Country]))

        MyappDepnp_obj = MyappDepnp(
            dpssn=EMSSN,
            dpname=EMNAME,
            dpsex=EMSEX,
            dpdoby=dob_parsed.year if dob_parsed else None,
            dpdobm=dob_parsed.month if dob_parsed else None,
            dpdobd=dob_parsed.day if dob_parsed else None,
            dpdssn = DPDSSN,
            dptype = relationship,
            dpadr1=full_address,
            dpcity=EMCITY,
            dpstate=EMST,
            dpmem=EMMEM,
            dpclas = ELCLAS,
            dpplan=ELPLAN
            
        )
        MyappDepnp_obj.save()

        return Response({"message": "Dependent added successfully!", "status": "success"})

    except Exception as e:
        return Response({"error": str(e)}, status=400)
    
@api_view(['POST'])
def add_dependents_db2(request):
    relationship = request.data.get("relationship")  
    if relationship == "Member":
        return Response({"error": "Only Dependents can be added. Invalid relationship type."}, status=400)

    emssn = request.data.get("emssn")  
    dpdssn = request.data.get("dpdssn")

    if not emssn:
        return Response({"error": "SSN (emssn) is required."}, status=400)

    if True:
        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()
        cursor.execute(f"SELECT dpseq FROM {schema_name}.depnp WHERE dpssn = ?", (emssn,))
        dpseq_values = cursor.fetchall()
        dpseq_values = [int(row[0]) for row in dpseq_values if row[0] is not None]
        new_seq = max(dpseq_values) + 1 if dpseq_values else 0
        print(f"New Sequence Value: {new_seq}")
        
        cursor.execute(f"SELECT COUNT(*) FROM {schema_name}.depnp WHERE dpdssn = ?", (dpdssn,))
        if cursor.fetchone()[0] > 0:
            return Response({"error": "SSN already exists. Duplicate entries are not allowed."}, status=400)

        dpname = request.data.get("dpname")
        dpsex = request.data.get("dpsex")
        dpdob = request.data.get("dpdob")  
        dpadr1 = request.data.get("dpadr1")
        dpcity = request.data.get("dpcity")
        dpst = request.data.get("dpst")
        country = request.data.get("country")  
        dpmem = request.data.get("dpmem")
        dpplan = request.data.get("dpplan")
        dpclas = request.data.get("dpclas")

        dob_parsed = None
        dpdoby = dpdobm = dpdobd = None
        if dpdob:
            try:
                dob_parsed = datetime.strptime(dpdob, "%Y-%m-%d")
                dpdoby = dob_parsed.year
                dpdobm = dob_parsed.month
                dpdobd = dob_parsed.day
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        full_address = ", ".join(filter(None, [dpadr1, dpcity, dpst, country]))
        if relationship == "Spouse" or relationship == 'spouse':
            dprltn = 1
        elif relationship == "Son" or relationship == 'son':
            dprltn = 2
        elif relationship == 'Daughter' or relationship == 'daughter':
            dprltn = 3
        elif relationship == 'Stepchild' or relationship == 'stepchild':
            dprltn = 4
        else:
            dprltn = 9

        current_date = datetime.today()

        year = str(current_date.year)
        month = str(current_date.month)
        day = str(current_date.day)
        status = 'A'
        
        check_query = """
            SELECT COUNT(*) FROM {schema}.DEPNP WHERE dpssn = ?
        """.format(schema=schema_name)

        cursor.execute(check_query, (emssn,))
        result = cursor.fetchone()

        # Step 2: Insert only if the record does not exist
        if result[0]> 0:
            insert_query = """
                INSERT INTO {schema}.DEPNP
                (dpname, dpsex, dpdoby, dpdobm, dpdobd, dpdssn, dpclas, dpplan, dprltn, 
                dpefdy, dpefdm, dpefdd, dpstat, dpupyy, dpupmm, dpupdd, dpssn,dpseq)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) WITH NC
            """.format(schema=schema_name)

            cursor.execute(insert_query, (dpname, dpsex, dpdoby, dpdobm, dpdobd, dpdssn, dpclas, dpplan, dprltn, 
                                        year, month, day, status, year, month, day, emssn,new_seq))
            connection.commit()
            print("Inserted successfully")

            print("Inserted successfully")
            return Response({"message": "Dependent added successfully!", "status": "success"})
        else:
            print("Record already exists, skipping insertion",result)
            return Response({"message": "Dependent already exists"})

        


    
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pyodbc
from datetime import datetime



class GetMemberInfoDB2(APIView):
    def get(self, request):
        name = request.GET.get('name')
        relationship = request.GET.get('relationship')
        ssn = request.GET.get('ssn')

        if not name and not relationship and not ssn:
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        connection = pyodbc.connect(connection_string)
        cursor = connection.cursor()

        try:
            if relationship.lower() == "member":
                member_query = f"SELECT * FROM {schema_name}.empyp WHERE emssn = ?"
                cursor.execute(member_query, (ssn,))
                member_row = cursor.fetchone()

                if not member_row:
                    return Response({"error": "Member not found"}, status=status.HTTP_404_NOT_FOUND)

                member_columns = [desc[0].lower() for desc in cursor.description]
                member = dict(zip(member_columns, member_row))
                print(">>>>>>>>>>>>>>>>>><<<<<<<<<<<<<<<<<<<<<<<")
                print(member.get('emdobm'), member.get('emdobd'), member.get('emdoby'))

                dob = self.format_dob(member.get('emdobm'), member.get('emdobd'), member.get('emdoby'))

                data = {
                    "name": member.get('emname', "name is not available"),
                    "ssn": member.get('emssn', "SSN is not available"),
                    "relationship": relationship,
                    "member_id": member.get('emmem#', "member ID is not available"),
                    "dob": dob if dob else "DOB is not available",
                    "address": member.get('emadr1', "address is not available"),
                    "state": member.get('emst', "state is not available"),
                    "city": member.get('emcity', "city is not available"),
                    "country": "USA"
                }

            else:
                dependent_query = f"SELECT * FROM {schema_name}.depnp WHERE dpdssn = ? AND dpname LIKE ?"
                cursor.execute(dependent_query, (ssn, f"%{name}%"))
                dependent_row = cursor.fetchone()

                if not dependent_row:
                    return Response({"error": "Dependent not found"}, status=status.HTTP_404_NOT_FOUND)

                dependent_columns = [desc[0].lower() for desc in cursor.description]
                dependent = dict(zip(dependent_columns, dependent_row))

                dob = self.format_dob(dependent.get('dpdobm'), dependent.get('dpdobd'), dependent.get('dpdoby'))

                member_query = f"SELECT * FROM {schema_name}.empyp WHERE emssn = ?"
                cursor.execute(member_query, (dependent.get('dpssn'),))
                member_row = cursor.fetchone()
                member = dict(zip([desc[0].lower() for desc in cursor.description], member_row)) if member_row else {}

                data = {
                    "name": dependent.get('dpname', "name is not available"),
                    "ssn": dependent.get('dpdssn', "SSN is not available"),
                    "relationship": dependent.get('dptype', "relationship is not available"),
                    "member_id": member.get('emmem', "member ID is not available"),
                    "dob": dob if dob else "DOB is not available",
                    "address": member.get('emadr1', "address is not available"),
                    "state": member.get('emst', "state is not available"),
                    "city": member.get('emcity', "city is not available"),
                    "country": "USA"
                }

        finally:
            cursor.close()
            connection.close()

        return Response(data, status=status.HTTP_200_OK)

    def format_dob(self, month, day, year):
        if not all([month, day, year]):
            return None

        try:
            # Convert Decimal to int
            month = int(month) if isinstance(month, Decimal) else month
            day = int(day) if isinstance(day, Decimal) else day
            year = int(year) if isinstance(year, Decimal) else year

            dob = datetime(year, month, day)
            return dob.strftime("%B %d, %Y")
        except (ValueError, TypeError):
            return None

    
        
class GetMemberInfo(APIView):
    def get(self, request):
        name = request.GET.get('name')
        relationship = request.GET.get('relationship')
        ssn = request.GET.get('ssn')

        if not name and not relationship and not ssn:
            return Response("All fields are required")
        
        if relationship.lower() == "member":
            member = MyappEmpyp.objects.filter(emssn=ssn).first()
            if not member:
                return Response({'error': 'Member not found'}, status=404)
            
            dob = self.format_dob(member.emdobm, member.emdobd, member.emdoby)
        
            data = {
                "name": member.emname if member.emname else "name is not available",
                "ssn": member.emssn if member.emssn else "SSN is not available",
                "relationship": relationship,
                "member_id": member.emmem if member.emmem else "member ID is not available",
                "dob": dob if dob else "DOB is not available",
                "address": member.emadr1 if member.emadr1 else "address is not available",
                "state": member.emst if member.emst else "state is not available",
                "city": member.emcity if member.emcity else "city is not available",
                "country": "USA"
            } 
        
        else:
            dependent = MyappDepnp.objects.filter(dpdssn=ssn, dpname__icontains=name).first()
            if not dependent:
                return Response({"error": "Dependent not found"}, status=404)

            dob = self.format_dob(dependent.dpdobm, dependent.dpdobd, dependent.dpdoby)

            member = MyappEmpyp.objects.filter(emssn=dependent.dpssn).first()

            data = {
                "name": dependent.dpname if dependent.dpname else "name is not available",
                "ssn": dependent.dpdssn if dependent.dpdssn else "SSN is not available",
                "relationship": dependent.dptype if dependent.dptype else "relationship is not available",
                "member_id": member.emmem if member and member.emmem else "member ID is not available",
                "dob": dob if dob else "DOB is not available",
                "address": member.emadr1 if member and member.emadr1 else "address is not available",
                "state": member.emst if member and member.emst else "state is not available",
                "city": member.emcity if member and member.emcity else "city is not available",
                "country": "USA"
            }

        return Response(data)      
    
    def format_dob(self, month, day, year):
        if not (month and day and year):
            return None
        try:
            dob = datetime(year, month, day)
            return dob.strftime("%B %d, %Y")
        except ValueError:
            return None
        

class UpdateMemberInfo(APIView):
    def post(self, request):
        name = request.data.get('name')
        relationship = request.data.get('relationship')
        ssn = request.data.get('ssn')
        member_id = request.data.get('member_id')
        dob_str = request.data.get('dob')  
        address = request.data.get('address')
        state = request.data.get('state')
        city = request.data.get('city')

        if not all([name, relationship, ssn, member_id, dob_str, address, state, city]):
            return Response({"error": "Missing required fields"}, status=400)

        year, month, day = self.parse_dob(dob_str)
        if not all([year, month, day]):
            return Response({"error": "Invalid date format. Expected format like 'mm-dd-yyyy'"}, status=400)

        if relationship.lower() == "member":
            instance = MyappEmpyp.objects.filter(emssn=ssn).first()
            if not instance:
                return Response({"error": "Member record not found"}, status=404)

            instance.emname = name
            instance.emssn = ssn
            instance.emmem = member_id
            instance.emdoby = year
            instance.emdobm = month
            instance.emdobd = day
            instance.emadr1 = address
            instance.emst = state
            instance.emcity = city
            instance.save()

            return Response({"message": "Member record updated successfully"})

        else:
            instance = MyappDepnp.objects.filter(dpdssn=ssn, dpname__icontains=name).first()
            if not instance:
                return Response({"error": "Dependent record not found"}, status=404)

            with transaction.atomic():
                rows_updated = MyappDepnp.objects.filter(id=instance.id).update(
                    dpname=name,
                    dpdssn=ssn,
                    dptype=relationship,
                    dpdoby=year,
                    dpdobm=month,
                    dpdobd=day,
                )

            if rows_updated == 0:
                return Response({"error": "Update failed!"}, status=500)
            
            return Response({"message": "Dependent record updated successfully"})

    def parse_dob(self, dob_str):
        try:
            dt = datetime.strptime(dob_str, "%m-%d-%Y") 
            return dt.year, dt.month, dt.day
        except Exception:
            return None, None, None
        

class UpdateMemberInfoDB2(APIView):
    def post(self, request):
        name = request.data.get('name')
        relationship = request.data.get('relationship')
        ssn = request.data.get('ssn')
        member_id = request.data.get('member_id')
        dob_str = request.data.get('dob')  
        address = request.data.get('address')
        state = request.data.get('state')
        city = request.data.get('city')
        dep_ssn = request.data.get('dep_ssn',None)

        if not all([name, relationship, ssn, member_id, dob_str, address, state, city]):
            return Response({"error": "Missing required fields"}, status=400)

        year, month, day = self.parse_dob(dob_str)
        if not all([year, month, day]):
            return Response({"error": "Invalid date format. Expected format like 'mm-dd-yyyy'"}, status=400)

        try:
            connection = pyodbc.connect(connection_string
            )
            cursor = connection.cursor()

            if relationship.lower() == "member":
                cursor.execute(f"SELECT * FROM {schema_name}.empyp WHERE EMSSN = ?", (ssn))
                row = cursor.fetchone()
                if not row:
                    return Response({"error": "Member record not found"}, status=404)

                cursor.execute(f"""
                    UPDATE {schema_name}.empyp
                    SET EMNAME = ?, EMSSN = ?, EMMEM# = ?, EMDOBY = ?, EMDOBM = ?, EMDOBD = ?, EMADR1 = ?, EMST = ?, EMCITY = ?
                    WHERE EMSSN = ? WITH NC
                """, (name, ssn, member_id, year, month, day, address, state, city, ssn))

            else:
                cursor.execute(f"SELECT * FROM {schema_name}.depnp WHERE DPDSSN = ? " ,(dep_ssn,))
                row = cursor.fetchone()
                if not row:
                    return Response({"error": "Dependent record not found"}, status=404)

                cursor.execute(f"""
                UPDATE {schema_name}.depnp
                SET "DPNAME" = ?, "DPDSSN" = ?, "DPDOBY" = ?, "DPDOBM" = ?, "DPDOBD" = ?
                WHERE "DPDSSN" = ? WITH NC
            """, (name, dep_ssn, year, month, day, dep_ssn))

            connection.commit()
            cursor.close()
            connection.close()

            return Response({"message": "Record updated successfully"})

        except pyodbc.Error as e:
            return Response({"error": str(e)}, status=500)

    def parse_dob(self, dob_str):
        try:
            dt = datetime.strptime(dob_str, "%m-%d-%Y") 
            return dt.year, dt.month, dt.day
        except Exception:
            return None, None, None



class MostRecentDataView(APIView):
    def get(self, request):
        latest_entry = MyappRecentData.objects.order_by('-file_date').first()
        if latest_entry:
            latest_date = latest_entry.file_date
            latest_entries = MyappRecentData.objects.filter(file_date=latest_date)
            serializer = MyappRecentDataSerializer(latest_entries, many=True)
            return Response(serializer.data)
        return Response({"message": "No data found"}, status=404)
    
class GetDateRecentDataView(APIView):
    def get(self,request):
        filedate = request.GET.get('recent_date')
        date_entries  = MyappRecentData.objects.filter(file_date = filedate)
        if date_entries:
            serializer = MyappRecentDataSerializer(date_entries,many=True)
            return Response(serializer.data)
        else:
            return Response("No data found for specified date")
    
class TermedMembersView(APIView):
    def get(self, request):
        latest_entry = MyappTermedMembers.objects.order_by('-file_date').first()
        if latest_entry:
            latest_date = latest_entry.file_date
            latest_entries =MyappTermedMembers.objects.filter(file_date=latest_date)
            serializer = MyappTermedMemberSerializer(latest_entries, many=True)
            return Response(serializer.data)
        return Response({"message": "No data found"}, status=404)
    

class AlternativeAddressTableCreate(APIView):
    def post(self, request, *args, **kwargs):
        serializer = AlternativeAddressTableSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AlternativeAddressTableUpdate(APIView):
    def post(self, request, *args, **kwargs):
        ssn = request.data.get('ssn', '')
        dep_ssn_list = request.data.get('dep_ssn', [])
        dep_name_list = request.data.get('dep_name', [])
        dep_relations_list = request.data.get('dep_relations', [])
        is_alternative = request.data.get('is_alternative', False)

        if is_alternative == "true":
            is_alternative = True

        if not ssn and not dep_ssn_list:
            return Response({"error": "SSN or DEPSSN is required to update the record"}, status=status.HTTP_400_BAD_REQUEST)

        if len(dep_ssn_list) != len(dep_name_list) or len(dep_ssn_list) != len(dep_relations_list):
            return Response({"error": "Mismatch in lengths of dep_ssn, dep_name, and dep_relations"}, status=status.HTTP_400_BAD_REQUEST)

        if is_alternative:
            instances = AlternativeAddressTable.objects.filter(ssn=ssn)
            if instances.count() > 1:
                existing_dep_ssn_set = set(instances.values_list('dep_ssn', flat=True))
                for dep_ssn, dep_name, dep_relation in zip(dep_ssn_list, dep_name_list, dep_relations_list):
                    record_data = request.data.copy()
                    record_data['dep_ssn'] = dep_ssn
                    record_data['last_first_name'] = dep_name
                    record_data['relationship'] = dep_relation

                    if str(dep_ssn) in existing_dep_ssn_set:
                        instance = AlternativeAddressTable.objects.get(ssn=ssn, dep_ssn=dep_ssn)
                        serializer = AlternativeAddressTableSerializer(instance, data=record_data, partial=False)
                        if serializer.is_valid():
                            serializer.save()
                    else:
                        serializer = AlternativeAddressTableSerializer(data=record_data)
                        if serializer.is_valid():
                            serializer.save()

            elif instances.count() == 1:
                for dep_ssn, dep_name, dep_relation in zip(dep_ssn_list, dep_name_list, dep_relations_list):
                    new_record_data = request.data.copy()
                    new_record_data['dep_ssn'] = dep_ssn
                    new_record_data['last_first_name'] = dep_name
                    new_record_data['relationship'] = dep_relation
                    serializer = AlternativeAddressTableSerializer(data=new_record_data)
                    if serializer.is_valid():
                        serializer.save()

            elif not instances.exists():
                print('great')
                new_record = AlternativeAddressTable.objects.create(
                last_first_name=request.data.get("last_first_name"),
                pay_to_seq=request.data.get("pay_to_seq"),
                address1=request.data.get("address1"),
                address2=request.data.get("address2"),
                address3=request.data.get("address3"),
                city=request.data.get("city"),
                state=request.data.get("state"),
                zip=request.data.get("zip"),
                relationship=request.data.get("relationship"),
                last_activity_date=request.data.get("last_activity_date"),
                employee_name=request.data.get("employee_name"),
                ssn=ssn,
                is_alternate_same=request.data.get("is_alternative"),
                dep_ssn=" ")
            
                for dep_ssn, dep_name, dep_relation in zip(dep_ssn_list, dep_name_list, dep_relations_list):
                    new_record_data = request.data.copy()
                    new_record_data['dep_ssn'] = dep_ssn
                    new_record_data['last_first_name'] = dep_name
                    new_record_data['relationship'] = dep_relation
                    serializer = AlternativeAddressTableSerializer(data=new_record_data)
                    if serializer.is_valid():
                        serializer.save()


            return Response({"message": "Records processed successfully"}, status=status.HTTP_200_OK)
        dep_flag = False
        if len(dep_ssn_list) == 1:
            dep_ssn = dep_ssn_list[0]
            instances = AlternativeAddressTable.objects.filter(dep_ssn=dep_ssn)
            dep_flag = True
        else:
            instances = AlternativeAddressTable.objects.filter(ssn=ssn, relationship="Member")

        if not instances.exists():
            return Response({"error": "No records found matching the criteria"}, status=status.HTTP_404_NOT_FOUND)

        updated_records = []
        print('hello',instances)
        for instance in instances:
            print("jake",instance)
            data = request.data.copy()
            print(data)
            if "dep_ssn" in data and data["dep_ssn"] is not None:
                data["dep_ssn"] = str(data["dep_ssn"])

            if len(dep_ssn_list) == 0 and len(dep_name_list) == 0 and len(dep_relations_list) == 0:
                serializer = AlternativeAddressTableSerializer(instance, data=data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    updated_records.append(serializer.data)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            else:
                for dep_ssn, dep_name, dep_relation in zip(dep_ssn_list, dep_name_list, dep_relations_list):
                    print('hell')
                    data["dep_ssn"] = dep_ssn
                    data["last_first_name"] = dep_name
                    data["relationship"] = dep_relation
                    print("help",instance)
                    serializer = AlternativeAddressTableSerializer(instance, data=data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        updated_records.append(serializer.data)
                    else:
                        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response({"message": "Records updated successfully", "updated_records": updated_records}, status=status.HTTP_200_OK)




class Get_AlternateAddressData(APIView):
    def get(self,request):
        dep_ssn = request.GET.get('dep_ssn','')
        ssn = request.GET.get('ssn','')
        total = request.GET.get('total',False)
        try:
            if total == 'True':
                total = True
            if ssn and total:
                data = list(AlternativeAddressTable.objects.filter(ssn=ssn).values())
                return Response(data)
            elif ssn:
                instance_data = AlternativeAddressTable.objects.filter(ssn=ssn, relationship="Member").first()
                data = model_to_dict(instance_data) if instance_data else None
                return Response(data)
            elif dep_ssn:
                instance_data = AlternativeAddressTable.objects.get(dep_ssn=dep_ssn)
                data = model_to_dict(instance_data) if instance_data else None
                return Response(data)
            else:
                return Response("SSN or DEP SSN is required")
        except:
            return Response("No record found for entered ssn")


class NotesEntryCreateView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = NotesEntrySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class NotesEntryListView(APIView):
    def get(self, request, *args, **kwargs):
        notes_entries = NotesEntry.objects.all()
        serializer = NotesEntrySerializer(notes_entries, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

class GetEligibilityData(APIView):
    def get(self, request):
        ssn = request.GET.get('ssn',None)
        dep_ssn = request.GET.get('dep_ssn',None)

        if not ssn or dep_ssn:
            return Response({"error": "SSN is required"}, status=status.HTTP_400_BAD_REQUEST)

        if ssn:
            try:
                record = MyappEmpyp.objects.get(EMSSN=ssn)  # Fetch record based on SSN
            except MyappEmpyp.DoesNotExist:
                return Response({"message": "No record found for the given SSN"}, status=status.HTTP_404_NOT_FOUND)

            # Define the specific fields you want to return
            response_data = {
                "status date": record.EMEFFDATE,
                "class code": record.EMCLAS,
                "health status": record.EMFLAG
            }

            return Response(response_data, status=status.HTTP_200_OK)
        
        elif dep_ssn:
            try:
                record = MyappDepnp.objects.get(DPDSSN=dep_ssn)  # Fetch record based on SSN
            except MyappDepnp.DoesNotExist:
                return Response({"message": "No record found for the given DPDSSN"}, status=status.HTTP_404_NOT_FOUND)

            # Define the specific fields you want to return
            response_data = {
                "status date": record.DPEFFDATE,
                "class code": record.DPCLAS,
                "health status": record.DPFLAG
            }

            return Response(response_data, status=status.HTTP_200_OK)


class GetEligibilityDataDB2(APIView):
    def get(self, request):
        ssn = request.GET.get('ssn', '')
        dep_ssn = request.GET.get('dep_ssn', '')
        mem_ssn = request.GET.get('mem_ssn','')
        dep_name = request.GET.get('name','')

        if not ssn and not dep_ssn:
            return Response({"error": "SSN or Dependent SSN is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Database connection details
        host = '10.68.4.201'
        port = '23'
        database = 'S06e6f1r'
        user = 'ONEADMIN'
        password = 'ONEADMIN'

        connection_string = (
            f"DRIVER={{iSeries Access ODBC Driver}};"
            f"SYSTEM={host};"
            f"PORT={port};"
            f"DATABASE={database};"
            f"UID={user};"
            f"PWD={password};"
            f"PROTOCOL=TCPIP;"
        )

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            response_data = {}

            if ssn:
                query = f"""SELECT ELEPDY, ELEPDM, ELEPDD, ELPLAN, ELCLAS, ELUDTY, ELUDTM, ELUDTD, ELDSEQ, ELHSTA, ELUSER,ELWSTA
                        FROM {schema_name}.elghp 
                        WHERE ELSSN = ? AND ELDSEQ = ?"""
                cursor.execute(query, (ssn, 0.0))
                rows = cursor.fetchall() 
                print("lenght",len(rows))
                if not rows:
                    return Response({"message": "No record found for the given SSN"}, status=status.HTTP_404_NOT_FOUND)

                records = []
                for row in rows:
                    elepdy, elepdm, elepdd, elplan, elclas, eludty, eludtm, eludtd,eldseq,elhsta,eluser,elwsta = row
                    emeffect_date = f"{str(elepdm).zfill(2)}/{str(elepdd).zfill(2)}/{str(elepdy).zfill(4)}"
                    last_updated_date = f"{str(eludtm).zfill(2)}/{str(eludtd).zfill(2)}/{str(eludty).zfill(4)}"

                    query = f"SELECT EMSTCD FROM {schema_name}.empyp WHERE EMSSN = ?"
                    cursor.execute(query, (ssn,))
                    health_status_row = cursor.fetchone()
                    health_status = health_status_row[0] if health_status_row else None

                    class_desc_list, current_class = get_class_name(str(elclas))
                    plan_desc = get_plan_name(str(elplan))
                    cob = check_COB(ssn)

                    records.append({
                        "status date": emeffect_date,  
                        "class code": elclas,  
                        "health status": health_status,  
                        "class desc list": class_desc_list,
                        "current class": current_class,
                        "plan desc": plan_desc,
                        "updated by": "user",
                        "last_updated_date": last_updated_date,
                        "eligibility_type": '',
                        "cob": cob,
                        "eldseq":eldseq,
                        "username":eluser,
                        "el_health_status":elhsta,
                        "weekly_status":elwsta
                    })

                return Response({"records": records}, status=status.HTTP_200_OK)

            elif dep_ssn :
                # seq_query = f"""SELECT DPSEQ FROM {schema_name}.depnp WHERE DPDSSN = ?"""
                # cursor.execute(seq_query, (dep_ssn,))
                # row = cursor.fetchone()
                # dpseq = row[0]
                # dpseq = float(dpseq)
                # query = f"""SELECT ELEPDY, ELEPDM, ELEPDD, ELPLAN, ELCLAS, ELUDTY, ELUDTM, ELUDTD, ELDSEQ, ELHSTA, ELUSER,ELWSTA
                #         FROM {schema_name}.elghp 
                #         WHERE ELSSN = ? AND ELDSEQ = ?"""
                # cursor.execute(query, (mem_ssn, dpseq))
                # rows = cursor.fetchall()  

                query = f"""
                    SELECT 
                        DPEFDY, DPEFDM, DPEFDD, DPPLAN, DPCLAS, DPUPYY, DPUPMM, DPUPDD,
                        DPSEQ, DPSTAT, DPUSER
                    FROM {schema_name}.depnp 
                    WHERE DPDSSN = ?
                """
                cursor.execute(query, (dep_ssn,))
                rows = cursor.fetchall()

                if not rows:
                    return Response({"message": "No record found for the given Dependent SSN"}, status=status.HTTP_404_NOT_FOUND)

                records = []
                for row in rows:
                    elepdy, elepdm, elepdd, elplan, elclas, eludty, eludtm, eludtd,eldseq,elhsta,eluser= row
                    emeffect_date = f"{str(elepdm).zfill(2)}/{str(elepdd).zfill(2)}/{str(elepdy).zfill(4)}"
                    last_updated_date = f"{str(eludtm).zfill(2)}/{str(eludtd).zfill(2)}/{str(eludty).zfill(4)}"

                    class_desc_list, current_class = get_class_name(str(elclas))
                    plan_desc = get_plan_name(str(elplan))
                    cob = check_COB(dep_ssn)

                    records.append({
                        "status date": emeffect_date,  
                        "class code": elclas,  
                        "health status": elhsta,  
                        "class desc list": class_desc_list,
                        "current class": current_class,
                        "plan desc": plan_desc,
                        "updated by": "user",
                        "last_updated_date": last_updated_date,
                        "eligibility_type": '',
                        "cob": cob,
                        "eldseq":eldseq,
                        "username":eluser,
                    })
                return Response({"records": records}, status=status.HTTP_200_OK)


        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateEligibilityDataDB2(APIView):
    def post(self, request):
        ssn = request.data.get("ssn", "")
        dep_ssn = request.data.get("dep_ssn", "")
        updated_data = request.data.get("updated_data", {})

        if not ssn and not dep_ssn:
            return Response({"error": "SSN or Dependent SSN is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            connection = pyodbc.connect(connection_string)
            cursor = connection.cursor()

            # Extract date components from `effdate`
            effdate = updated_data.get("effdate", "")
            if effdate:
                elepdm, elepdd, elepdy = effdate.split("/")  # Extract MM/DD/YYYY

            # Extract date components from `last_updated_date`
            last_updated_date = updated_data.get("last_updated_date", "")
            if last_updated_date:
                eludtm, eludtd, eludty = last_updated_date.split("/")  # Extract MM/DD/YYYY

            cursor.execute(f"SELECT ELDSEQ FROM {schema_name}.ELGHP WHERE ELSSN = ?", (ssn,))
            dpseq_values = cursor.fetchall()
            dpseq_values = [int(row[0]) for row in dpseq_values if row[0] is not None]

            new_seq = max(dpseq_values) + 1 if dpseq_values else 0

            print(f"New Sequence Value: {new_seq}")

            if ssn:
                update_query = f"""
                    UPDATE {schema_name}.elghp 
                    SET ELEPDY=?, ELEPDM=?, ELEPDD=?, ELPLAN=?, ELCLAS=?, 
                        ELUDTY=?, ELUDTM=?, ELUDTD=?, ELHSTA=? 
                    WHERE ELSSN=? WITH NC
                """
                cursor.execute(update_query, (
                    elepdy, elepdm, elepdd, updated_data.get("elplan"),
                    updated_data.get("elclas"), eludty, eludtm, eludtd,
                    updated_data.get("elhsta"), ssn
                ))

                connection.commit()

                update_stat_query = f"""
                    UPDATE {schema_name}.empyp
                    SET EMSTCD = ?, EMUPYY = ?,EMUPMM = ?,EMUPDD = ?
                    WHERE EMSSN = ? WITH NC
                """
                cursor.execute(update_stat_query,(updated_data.get('emstcd'),eludty,eludtm,eludtd,ssn))
                connection.commit()
            
            elif dep_ssn:
                update_query = f"""
                    UPDATE {schema_name}.depnp 
                    SET DPEFDY = ?, DPEFDM = ?, DPEFDD = ?, 
                        DPCLAS = ?, DPPLAN = ?, DPSTAT = ?, 
                        DPUPYY = ?, DPUPMM = ?, DPUPDD = ? 
                    WHERE DPDSSN = ? WITH NC
                """
                cursor.execute(update_query, (
                    elepdy, elepdm, elepdd,
                    updated_data.get("dpclas"),
                    updated_data.get("dpplan"),
                    updated_data.get("dpstat"),
                    eludty, eludtm, eludtd,
                    dep_ssn
                ))
                connection.commit()

            connection.commit()
            return Response({"message": f"Record updated successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()




import pyodbc
import os

port = '23'
host = '104.153.122.227'
database = 'S78F13CW'
user = 'onetgart'
password = 'abcpass21'


def map_network_drive(drive_letter, network_path, username, password):
    try:
        # Command to map the network drive
        command = f'net use {drive_letter} {network_path} {password} /user:{username}'
        os.system(command)
        print(f"Network drive {drive_letter} mapped successfully.")
    except Exception as e:
        print(f"Error mapping network drive: {e}")


def call_stored_procedure_pdf(ssn, ssn_path, ssn_file):

   
    drive_letter = 'V:'
    network_path = r'\\104.153.122.227\HOME\DURGA'
    map_network_drive(drive_letter, network_path, user, password)


    connection_string = (
        f"DRIVER={{iSeries Access ODBC Driver}};" 
        f"SYSTEM={host};"
        f"PORT={port};"
        f"DATABASE={database};"
        f"UID={user};"
        f"PWD={password};"
        f"PROTOCOL=TCPIP;"
        f"CURRENTSCHEMA=QGPL;" 
    )

    param1 = ssn
    param2 = ssn_path
    param3 = ssn_file

    try:
        conn = pyodbc.connect(connection_string)
        cursor = conn.cursor()

        cursor.execute(
            "CALL QGPL.OOE_PROD_RUN_CL0164AS(?, ?, ?)", 
            (param1, param2, param3)
        )
        conn.commit()
        print("Stored procedure executed successfully.")
        return f"{drive_letter}\\{param3}"

    except pyodbc.Error as e:
        print(f"Error occurred: {e}")

    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()

@api_view(['GET'])
def generate_pdf(request):
    claim_no = request.GET.get('claim_no')
    ssn_path = "/HOME/DURGA"
    ssn_file = f"{claim_no}.pdf"
    print(claim_no)
    file_path = call_stored_procedure_pdf(claim_no, ssn_path, ssn_file)

    if file_path and os.path.exists(file_path):
        return FileResponse(open(file_path, "rb"), content_type="application/pdf")
    
    return JsonResponse({"error": "PDF file not found."}, status=404)


class GetDataByTermDate(APIView):
    def get(self, request):
        term_date = request.query_params.get("term_date")

        if not term_date:
            return Response({"error": "term_date parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            matching_records = MyappTermedMembers.objects.filter(file_date=term_date)

            if not matching_records.exists():
                return Response({"message": "No records found"}, status=status.HTTP_404_NOT_FOUND)

            data = list(matching_records.values())
            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
