import os
from typing import List
import pandas as pd
import numpy as np
from pathlib import Path

from pii_codex.models.common import (
    RiskLevel,
    RiskAssessment,
    RiskLevelDefinition,
    ClusterMembershipType,
    HIPAACategory,
    DHSCategory,
    NISTCategory,
)
from pii_codex.utils.file_util import delete_folder, delete_file, write_json_file

dirname = os.path.dirname(__file__)

# region PII MAPPING AND RATING UTILS


def calculate_average_risk_score(risk_assessments: List[RiskAssessment]) -> float:
    """
    Returns the average risk score per token
    @param risk_assessments:
    @return:
    """
    return np.mean([risk_level.risk_level_value for risk_level in risk_assessments])


def map_pii_type(pii_type: str) -> RiskAssessment:
    """
    Maps the PII Type to a full RiskAssessment including categories it belongs to, risk level, and
    its location in the text.

    @param pii_type:
    @return:
    """
    pii_data_frame = open_pii_type_mapping_json("v1")

    information_detail_lookup = pii_data_frame[pii_data_frame.PII_Type == pii_type]

    # if not information_detail_lookup:
    #     raise Exception("PII type not found")

    # Retrieve the risk_level name by the value of the risk definition enum entry
    risk_level_definition = RiskLevelDefinition(
        information_detail_lookup.Risk_Level.item()
    )

    return RiskAssessment(
        pii_type_detected=pii_type,
        risk_level=RiskLevel[risk_level_definition.name],
        risk_level_definition=risk_level_definition,
        cluster_membership_type=ClusterMembershipType(
            information_detail_lookup.Cluster_Membership_Type.item()
        ),
        hipaa_category=HIPAACategory[
            information_detail_lookup.HIPAA_Protected_Health_Information_Category.item()
        ],
        dhs_category=DHSCategory(information_detail_lookup.DHS_Category.item()),
        nist_category=NISTCategory(information_detail_lookup.NIST_Category.item()),
    )


# endregion


# region MAPPING FILE UTILS


def open_pii_type_mapping_csv(
    mapping_file_version: str = "v1", mapping_file_name: str = "pii_type_mappings"
):
    """

    @param mapping_file_name:
    @param mapping_file_version:
    """
    filename = os.path.join(
        dirname, f"../data/{mapping_file_version}/{mapping_file_name}.csv"
    )
    path = Path(__file__).parent / filename
    with path.open() as f:
        return pd.read_csv(f)


def open_pii_type_mapping_json(
    mapping_file_version: str = "v1", mapping_file_name: str = "pii_type_mappings"
):
    """

    @param mapping_file_name:
    @param mapping_file_version:
    @return:
    """
    filename = os.path.join(
        dirname, f"../data/{mapping_file_version}/{mapping_file_name}.json"
    )

    path = Path(__file__).parent / filename
    with path.open() as f:
        json_file_dataframe = pd.read_json(f)
        json_file_dataframe.drop("index", axis=1, inplace=True)

        return json_file_dataframe


def convert_pii_type_mapping_csv_to_json(
    data_frame: pd.DataFrame,
    mapping_file_version: str = "v1",
    json_file_name: str = "pii_type_mappings",
):
    """
    Writes JSON mapping file given a dataframe. Used primarily to update data folder with new versions

    @param data_frame:
    @param mapping_file_version:
    @param json_file_name:
    """

    folder_path = os.path.join(dirname, f"../data/{mapping_file_version}")

    file_path = os.path.join(
        dirname, f"../data/{mapping_file_version}/{json_file_name}.json"
    )

    write_json_file(
        folder_name=folder_path,
        file_name=file_path,
        json_data=data_frame.reset_index().to_json(orient="records"),
    )


def delete_mapping_file(
    mapping_file_version: str = "v1",
    json_file_name: str = "pii_type_mappings",
):
    """
    Deletes a version file within a data version folder

    @param mapping_file_version:
    @param json_file_name:
    """

    file_path = os.path.join(
        dirname, f"../data/{mapping_file_version}/{json_file_name}.json"
    )

    delete_file(file_path)


def delete_mapping_folder(
    mapping_file_version: str,
):
    """
    Deletes a version folder within the data folder

    @param mapping_file_version:
    """

    folder_path = os.path.join(dirname, f"../data/{mapping_file_version}")
    delete_folder(folder_path)


# endregion