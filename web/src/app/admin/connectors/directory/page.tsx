"use client";

import * as Yup from "yup";
import { DirectoryIcon, TrashIcon } from "@/components/icons/icons";
import { TextFormField } from "@/components/admin/connectors/Field";
import { HealthCheckBanner } from "@/components/health/healthcheck";
import { CredentialForm } from "@/components/admin/connectors/CredentialForm";
import {
//   DirectoryCredentialJson,
  DirectoryConfig,
  ConnectorIndexingStatus,
} from "@/lib/types";
import useSWR, { useSWRConfig } from "swr";
import { fetcher } from "@/lib/fetcher";
import { LoadingAnimation } from "@/components/Loading";
import { adminDeleteCredential, linkCredential } from "@/lib/credential";
import { ConnectorForm } from "@/components/admin/connectors/ConnectorForm";
import { ConnectorsTable } from "@/components/admin/connectors/table/ConnectorsTable";
import { usePopup } from "@/components/admin/connectors/Popup";
import { usePublicCredentials } from "@/lib/hooks";

const Main = () => {
  const { popup, setPopup } = usePopup();

  const { mutate } = useSWRConfig();
  const {
    data: connectorIndexingStatuses,
    isLoading: isConnectorIndexingStatusesLoading,
    error: isConnectorIndexingStatusesError,
  } = useSWR<ConnectorIndexingStatus<any, any>[]>(
    "/api/manage/admin/connector/indexing-status",
    fetcher
  );
//   const {
//     data: credentialsData,
//     isLoading: isCredentialsLoading,
//     error: isCredentialsError,
//     refreshCredentials,
//   } = usePublicCredentials();

  if (!connectorIndexingStatuses && isConnectorIndexingStatusesLoading) {
    return <LoadingAnimation text="Loading" />;
  }

  if (isConnectorIndexingStatusesError || !connectorIndexingStatuses) {
    return <div>Failed to load connectors</div>;
  }

  const directoryConnectorIndexingStatuses: ConnectorIndexingStatus<
    DirectoryConfig,
    // DirectoryCredentialJson
    {}
  >[] = connectorIndexingStatuses.filter(
    (connectorIndexingStatus) =>
      connectorIndexingStatus.connector.source === "directory"
  );

  return (
    <>
      {popup}
    
      {directoryConnectorIndexingStatuses.length > 0 && (
        <>
          <h2 className="font-bold mb-2 mt-6 ml-auto mr-auto">
            Directory indexing status
          </h2>
          <div className="mb-2">
            <ConnectorsTable<DirectoryConfig, {}>
              connectorIndexingStatuses={directoryConnectorIndexingStatuses}
            //   liveCredential={directoryCredential}
            //   getCredential={(credential) => {
            //     return (
            //       <div>
            //         <p>{credential.credential_json.bookstack_api_token_id}</p>
            //       </div>
            //     );
            //   }}
            //   onCredentialLink={async (connectorId) => {
            //     if (directoryCredential) {
            //       await linkCredential(connectorId, directoryCredential.id);
            //       mutate("/api/manage/admin/connector/indexing-status");
            //     }
            //   }}
              onUpdate={() =>
                mutate("/api/manage/admin/connector/indexing-status")
              }
            />
          </div>
        </>
      )}

      {directoryConnectorIndexingStatuses.length === 0 && (
          <>
            <div className="border-solid border-gray-600 border rounded-md p-6 mt-4">
              <h2 className="font-bold mb-3">Create Connection</h2>
              <p className="text-sm mb-4">
                Press connect below to start directory indexing.
              </p>
              <ConnectorForm<DirectoryConfig>
                nameBuilder={(values) => `DirectoryConnector`}
                source="directory"
                inputType="load_state" // or "poll"
                formBody={<></>}
                validationSchema={Yup.object().shape({})}
                initialValues={{}}
                refreshFreq={1 * 60} // 1 minute
                onSubmit={async (isSuccess, responseJson) => {
                  if (isSuccess && responseJson) {
                    await linkCredential(responseJson.id, 0);
                    mutate("/api/manage/admin/connector/indexing-status");
                  }
                }}
              />
            </div>
          </>
        )}
    </>
  );
};

export default function Page() {
  return (
    <div className="mx-auto container">
      <div className="mb-4">
        <HealthCheckBanner />
      </div>
      <div className="border-solid border-gray-600 border-b mb-4 pb-2 flex">
        <DirectoryIcon size={32} />
        <h1 className="text-3xl font-bold pl-2">Directory</h1>
      </div>
      <Main />
    </div>
  );
}
